"""Intel AMT WS-MAN client for direct HTTP/SOAP communication."""
from __future__ import annotations

import asyncio
import logging
import uuid
import xml.etree.ElementTree as ET
from enum import IntEnum
from typing import Any

import aiohttp
from aiohttp import BasicAuth

_LOGGER = logging.getLogger(__name__)

# AMT power state codes (CIM standard)
class PowerState(IntEnum):
    ON = 2
    SLEEP_LIGHT = 3
    SLEEP_DEEP = 4
    POWER_CYCLE_OFF_SOFT = 5
    POWER_OFF_HARD = 6  # read-only state, used for status
    HIBERNATE = 7
    POWER_OFF_SOFT = 8
    MASTER_BUS_RESET = 10
    POWER_CYCLE_OFF_HARD = 11
    SOFT_OFF = 12
    SOFT_RESET = 14
    NMI = 15

POWER_STATE_NAMES = {
    0: "Unknown",
    1: "Other",
    2: "On",
    3: "Sleep - Light",
    4: "Sleep - Deep",
    5: "Power Cycle (Off-Soft)",
    6: "Off - Hard",
    7: "Hibernate (Off-Soft)",
    8: "Off - Soft",
    9: "Power Cycle (Off-Hard)",
    10: "Master Bus Reset",
    11: "Diagnostic Interrupt (NMI)",
    12: "Off - Soft Graceful",
    13: "Off - Hard Graceful",
    14: "Master Bus Reset Graceful",
    15: "Power Cycle (Off - Soft Graceful)",
    16: "Power Cycle (Off - Hard Graceful)",
}

# WSMAN XML namespaces
NS = {
    "s": "http://www.w3.org/2003/05/soap-envelope",
    "wsa": "http://schemas.xmlsoap.org/ws/2004/08/addressing",
    "wsman": "http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd",
    "n1": "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_PowerManagementService",
    "n2": "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_AssociatedPowerManagementService",
}

WSMAN_POWER_SERVICE_URI = (
    "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_PowerManagementService"
)
WSMAN_ASSOC_POWER_URI = (
    "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_AssociatedPowerManagementService"
)
WSMAN_COMPUTER_SYSTEM_URI = (
    "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ComputerSystem"
)

# SOAP envelope for RequestPowerStateChange
POWER_ACTION_ENVELOPE = """\
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope
  xmlns:s="http://www.w3.org/2003/05/soap-envelope"
  xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
  xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd"
  xmlns:n1="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_PowerManagementService">
  <s:Header>
    <wsa:Action s:mustUnderstand="true">
      http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_PowerManagementService/RequestPowerStateChange
    </wsa:Action>
    <wsa:To s:mustUnderstand="true">{uri}</wsa:To>
    <wsman:ResourceURI s:mustUnderstand="true">
      http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_PowerManagementService
    </wsman:ResourceURI>
    <wsa:MessageID s:mustUnderstand="true">uuid:{msg_id}</wsa:MessageID>
    <wsa:ReplyTo>
      <wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>
    </wsa:ReplyTo>
    <wsman:SelectorSet>
      <wsman:Selector wsman:Name="Name">Intel(r) AMT Power Management Service</wsman:Selector>
      <wsman:Selector wsman:Name="SystemName">Intel(r) AMT</wsman:Selector>
      <wsman:Selector wsman:Name="CreationClassName">CIM_PowerManagementService</wsman:Selector>
      <wsman:Selector wsman:Name="SystemCreationClassName">CIM_ComputerSystem</wsman:Selector>
    </wsman:SelectorSet>
  </s:Header>
  <s:Body>
    <n1:RequestPowerStateChange_INPUT>
      <n1:PowerState>{power_state}</n1:PowerState>
      <n1:ManagedElement>
        <wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>
        <wsa:ReferenceParameters>
          <wsman:ResourceURI>http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ComputerSystem</wsman:ResourceURI>
          <wsman:SelectorSet>
            <wsman:Selector wsman:Name="Name">ManagedSystem</wsman:Selector>
            <wsman:Selector wsman:Name="CreationClassName">CIM_ComputerSystem</wsman:Selector>
          </wsman:SelectorSet>
        </wsa:ReferenceParameters>
      </n1:ManagedElement>
    </n1:RequestPowerStateChange_INPUT>
  </s:Body>
</s:Envelope>"""

# SOAP envelope for enumerating power state
POWER_STATE_ENUMERATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope
  xmlns:s="http://www.w3.org/2003/05/soap-envelope"
  xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
  xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd"
  xmlns:wsen="http://schemas.xmlsoap.org/ws/2004/09/enumeration">
  <s:Header>
    <wsa:Action s:mustUnderstand="true">
      http://schemas.xmlsoap.org/ws/2004/09/enumeration/Enumerate
    </wsa:Action>
    <wsa:To s:mustUnderstand="true">{uri}</wsa:To>
    <wsman:ResourceURI s:mustUnderstand="true">
      http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_AssociatedPowerManagementService
    </wsman:ResourceURI>
    <wsa:MessageID s:mustUnderstand="true">uuid:{msg_id}</wsa:MessageID>
    <wsa:ReplyTo>
      <wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>
    </wsa:ReplyTo>
    <wsman:Filter Dialect="http://schemas.dmtf.org/wbem/wsman/1/wsman/associationFilter">
      <wsman:AssociationFilter>
        <wsman:Object>
          <wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>
          <wsa:ReferenceParameters>
            <wsman:ResourceURI>http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ComputerSystem</wsman:ResourceURI>
            <wsman:SelectorSet>
              <wsman:Selector wsman:Name="Name">ManagedSystem</wsman:Selector>
              <wsman:Selector wsman:Name="CreationClassName">CIM_ComputerSystem</wsman:Selector>
            </wsman:SelectorSet>
          </wsa:ReferenceParameters>
        </wsman:Object>
        <wsman:AssociationClassName>CIM_AssociatedPowerManagementService</wsman:AssociationClassName>
      </wsman:AssociationFilter>
    </wsman:Filter>
  </s:Header>
  <s:Body>
    <wsen:Enumerate/>
  </s:Body>
</s:Envelope>"""

# Pull envelope (after enumerate)
POWER_STATE_PULL = """\
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope
  xmlns:s="http://www.w3.org/2003/05/soap-envelope"
  xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
  xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd"
  xmlns:wsen="http://schemas.xmlsoap.org/ws/2004/09/enumeration">
  <s:Header>
    <wsa:Action s:mustUnderstand="true">
      http://schemas.xmlsoap.org/ws/2004/09/enumeration/Pull
    </wsa:Action>
    <wsa:To s:mustUnderstand="true">{uri}</wsa:To>
    <wsman:ResourceURI s:mustUnderstand="true">
      http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_AssociatedPowerManagementService
    </wsman:ResourceURI>
    <wsa:MessageID s:mustUnderstand="true">uuid:{msg_id}</wsa:MessageID>
    <wsa:ReplyTo>
      <wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>
    </wsa:ReplyTo>
  </s:Header>
  <s:Body>
    <wsen:Pull>
      <wsen:EnumerationContext>{context}</wsen:EnumerationContext>
      <wsen:MaxElements>1</wsen:MaxElements>
    </wsen:Pull>
  </s:Body>
</s:Envelope>"""


class AMTConnectionError(Exception):
    """Raised when connection to AMT device fails."""


class AMTAuthError(Exception):
    """Raised when authentication to AMT device fails."""


class AMTCommandError(Exception):
    """Raised when an AMT command fails."""


class AMTClient:
    """Async client for Intel AMT WS-MAN API."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 16992,
        tls: bool = False,
        timeout: int = 10,
    ) -> None:
        """Initialize the AMT client."""
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.tls = tls
        self.timeout = timeout
        scheme = "https" if tls else "http"
        self.base_url = f"{scheme}://{host}:{port}"
        self.wsman_url = f"{self.base_url}/wsman"

    async def _post(self, body: str) -> str:
        """Send a SOAP POST request to the AMT device."""
        auth = aiohttp.BasicAuth(self.username, self.password)
        headers = {
            "Content-Type": "application/soap+xml; charset=UTF-8",
        }
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                auth=auth,
            ) as session:
                async with session.post(
                    self.wsman_url,
                    data=body.encode("utf-8"),
                    headers=headers,
                ) as resp:
                    if resp.status == 401:
                        raise AMTAuthError(
                            f"Authentication failed for {self.host}"
                        )
                    if resp.status not in (200, 500):
                        raise AMTConnectionError(
                            f"Unexpected HTTP {resp.status} from {self.host}"
                        )
                    return await resp.text()
        except aiohttp.ClientConnectorError as err:
            raise AMTConnectionError(
                f"Cannot connect to {self.host}:{self.port} - {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise AMTConnectionError(
                f"Timeout connecting to {self.host}:{self.port}"
            ) from err

    async def async_get_power_state(self) -> dict[str, Any]:
        """Query the current power state of the managed system."""
        msg_id = str(uuid.uuid4())
        body = POWER_STATE_ENUMERATE.format(
            uri=self.wsman_url,
            msg_id=msg_id,
        )

        try:
            response = await self._post(body)
        except Exception:
            raise

        # Parse enumeration context
        try:
            root = ET.fromstring(response)
            # Extract enumeration context
            context_el = root.find(
                ".//{http://schemas.xmlsoap.org/ws/2004/09/enumeration}EnumerationContext"
            )
            if context_el is None:
                _LOGGER.debug("Enumerate response: %s", response)
                raise AMTCommandError("No enumeration context in response")
            context = context_el.text
        except ET.ParseError as err:
            raise AMTCommandError(f"Invalid XML response: {err}") from err

        # Pull the result
        pull_msg_id = str(uuid.uuid4())
        pull_body = POWER_STATE_PULL.format(
            uri=self.wsman_url,
            msg_id=pull_msg_id,
            context=context,
        )
        pull_response = await self._post(pull_body)

        try:
            pull_root = ET.fromstring(pull_response)
            ps_el = pull_root.find(
                ".//{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_AssociatedPowerManagementService}PowerState"
            )
            req_ps_el = pull_root.find(
                ".//{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_AssociatedPowerManagementService}RequestedPowerState"
            )

            power_state_code = int(ps_el.text) if ps_el is not None else 0
            power_state_name = POWER_STATE_NAMES.get(power_state_code, "Unknown")
            requested_state = int(req_ps_el.text) if req_ps_el is not None else None

            return {
                "power_state_code": power_state_code,
                "power_state": power_state_name,
                "is_on": power_state_code == 2,
                "requested_state": requested_state,
                "raw": pull_response,
            }
        except (ET.ParseError, TypeError, ValueError) as err:
            _LOGGER.warning("Failed to parse power state response: %s", err)
            _LOGGER.debug("Pull response: %s", pull_response)
            raise AMTCommandError(f"Failed to parse power state: {err}") from err

    async def async_request_power_state_change(
        self, target_state: int
    ) -> bool:
        """Send a power state change command."""
        msg_id = str(uuid.uuid4())
        body = POWER_ACTION_ENVELOPE.format(
            uri=self.wsman_url,
            msg_id=msg_id,
            power_state=target_state,
        )

        response = await self._post(body)

        try:
            root = ET.fromstring(response)
            # Look for ReturnValue - 0 means success
            rv_el = root.find(
                ".//{http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_PowerManagementService}ReturnValue"
            )
            if rv_el is not None:
                rv = int(rv_el.text)
                if rv != 0:
                    raise AMTCommandError(
                        f"Power state change returned error code {rv}"
                    )
            return True
        except ET.ParseError as err:
            raise AMTCommandError(f"Invalid XML in power response: {err}") from err

    async def async_power_on(self) -> bool:
        """Power on the system."""
        return await self.async_request_power_state_change(PowerState.ON)

    async def async_power_off(self) -> bool:
        """Hard power off."""
        return await self.async_request_power_state_change(PowerState.POWER_OFF_HARD)

    async def async_soft_power_off(self) -> bool:
        """Graceful/soft power off (requires OS + LMS)."""
        return await self.async_request_power_state_change(PowerState.SOFT_OFF)

    async def async_reset(self) -> bool:
        """Hard reset (master bus reset)."""
        return await self.async_request_power_state_change(PowerState.MASTER_BUS_RESET)

    async def async_soft_reset(self) -> bool:
        """Soft/graceful reset (requires OS + LMS)."""
        return await self.async_request_power_state_change(PowerState.SOFT_RESET)

    async def async_power_cycle(self) -> bool:
        """Power cycle (soft)."""
        return await self.async_request_power_state_change(
            PowerState.POWER_CYCLE_OFF_SOFT
        )

    async def async_hibernate(self) -> bool:
        """Put system into hibernate."""
        return await self.async_request_power_state_change(PowerState.HIBERNATE)

    async def async_nmi(self) -> bool:
        """Send Non-Maskable Interrupt (diagnostic)."""
        return await self.async_request_power_state_change(PowerState.NMI)

    async def async_test_connection(self) -> dict[str, Any]:
        """Test connectivity and authentication. Returns device info."""
        # Just try to get power state - if it works, we're connected
        try:
            state = await self.async_get_power_state()
            return {"success": True, "power_state": state}
        except AMTAuthError:
            raise
        except AMTConnectionError:
            raise
        except Exception as err:
            raise AMTConnectionError(str(err)) from err
