"""
Weather Bot - A bot that provides weather information for locations.

This bot demonstrates how to make API calls to a weather service
and format the results for the user.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, TypedDict, Union, cast

import httpx
from fastapi_poe.types import MetaResponse, PartialResponse, QueryRequest

from utils.base_bot import BaseBot, BotError, BotErrorNoRetry

logger = logging.getLogger(__name__)


class WeatherCondition(TypedDict):
    """Type definition for a weather condition."""

    id: int
    main: str
    description: str
    icon: str


class MainWeatherData(TypedDict):
    """Type definition for main weather data."""

    temp: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int


class WindData(TypedDict):
    """Type definition for wind data."""

    speed: float
    deg: int


class CloudData(TypedDict):
    """Type definition for cloud data."""

    all: int


class SysData(TypedDict):
    """Type definition for sys data."""

    country: str
    sunrise: int
    sunset: int


class WeatherData(TypedDict, total=False):
    """Type definition for complete weather data response."""

    name: str
    main: MainWeatherData
    weather: List[WeatherCondition]
    wind: WindData
    clouds: CloudData
    sys: SysData
    dt: int
    timezone: int
    id: int
    cod: int
    mock_data: bool  # Optional field for mock data


class WeatherBot(BaseBot):
    """
    A bot that provides weather information for any location.

    Note: You need to set OPENWEATHER_API_KEY in your environment variables for this to work.
    You can get a free API key from https://openweathermap.org/
    """

    bot_name: str = "WeatherBot"
    bot_description: str = (
        "A bot that provides weather information. Just tell me a city or location."
    )
    version: str = "1.0.0"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the WeatherBot."""
        super().__init__(**kwargs)
        self.api_key: str = os.environ.get("OPENWEATHER_API_KEY", "")
        if not self.api_key:
            logger.warning("OPENWEATHER_API_KEY not set. Weather data will be mocked.")

    async def _get_weather(self, location: str) -> WeatherData:
        """
        Get weather data for a location.

        Args:
            location: The city or location name

        Returns:
            Dictionary containing weather data

        Raises:
            BotErrorNoRetry: If the location is not found
            BotError: If there is an error accessing the weather API
        """
        if not self.api_key:
            return self._get_mock_weather(location)

        try:
            # Use the OpenWeatherMap API for weather data
            url: str = "https://api.openweathermap.org/data/2.5/weather"
            params: Dict[str, str] = {
                "q": location,
                "appid": self.api_key,
                "units": "metric",  # Use metric units (Celsius)
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return cast(WeatherData, response.json())

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise BotErrorNoRetry(f"Location '{location}' not found.")
            logger.error(f"HTTP error in weather API: {e.response.text}")
            raise BotError(f"Weather API error: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")
            raise BotError(f"Failed to get weather data: {str(e)}")

    def _get_mock_weather(self, location: str) -> WeatherData:
        """
        Return mock weather data for testing.

        Args:
            location: The location name to use in the mock data

        Returns:
            Mock weather data
        """
        # Get current timestamp
        current_timestamp: int = int(datetime.now().timestamp())

        return cast(
            WeatherData,
            {
                "name": location,
                "main": {
                    "temp": 22.5,
                    "feels_like": 23.0,
                    "temp_min": 20.0,
                    "temp_max": 25.0,
                    "pressure": 1012,
                    "humidity": 65,
                },
                "weather": [
                    {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
                ],
                "wind": {"speed": 3.6, "deg": 160},
                "clouds": {"all": 0},
                "sys": {
                    "country": "Mock",
                    "sunrise": current_timestamp,
                    "sunset": current_timestamp + 43200,  # 12 hours later
                },
                "dt": current_timestamp,
                "timezone": 0,
                "id": 123456,
                "cod": 200,
                "mock_data": True,  # Flag to indicate this is mock data
            },
        )

    def _format_weather_data(self, weather_data: WeatherData) -> str:
        """
        Format weather data into a readable response.

        Args:
            weather_data: Weather data from API or mock

        Returns:
            Formatted weather information
        """
        location: str = weather_data.get("name", "Unknown")
        country: str = weather_data.get("sys", {}).get("country", "")

        # Get main weather data
        main_data: Dict[str, Any] = cast(Dict[str, Any], weather_data.get("main", {}))
        temp: float = float(main_data.get("temp", 0))
        feels_like: float = float(main_data.get("feels_like", 0))
        temp_min: float = float(main_data.get("temp_min", 0))
        temp_max: float = float(main_data.get("temp_max", 0))
        humidity: int = int(main_data.get("humidity", 0))

        # Get weather description
        weather_list = cast(List[Dict[str, Any]], weather_data.get("weather", [{}]))
        weather_main: str = str(
            weather_list[0].get("main", "Unknown") if weather_list else "Unknown"
        )
        weather_desc: str = str(
            weather_list[0].get("description", "Unknown") if weather_list else "Unknown"
        )

        # Get wind data
        wind: Dict[str, Any] = cast(Dict[str, Any], weather_data.get("wind", {}))
        wind_speed: float = wind.get("speed", 0)

        # Get time information
        dt: int = weather_data.get("dt", 0)
        timezone_offset: int = weather_data.get("timezone", 0)
        local_time: str = datetime.utcfromtimestamp(dt + timezone_offset).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Create response
        if weather_data.get("mock_data", False):
            response = f"## 🌤️ Weather for {location}\n\n"
            response += (
                "⚠️ **Note:** Using mock data. Set OPENWEATHER_API_KEY for real weather data.\n\n"
            )
        else:
            response = f"## 🌤️ Weather for {location}, {country}\n\n"

        # Current conditions
        response += f"**Current Conditions:** {weather_main} ({weather_desc})\n\n"
        response += "### Temperature\n"
        response += f"- **Current:** {temp}°C\n"
        response += f"- **Feels Like:** {feels_like}°C\n"
        response += f"- **Min/Max:** {temp_min}°C / {temp_max}°C\n\n"

        # Additional information
        response += "### Additional Info\n"
        response += f"- **Humidity:** {humidity}%\n"
        response += f"- **Wind Speed:** {wind_speed} m/s\n"
        response += f"- **Local Time:** {local_time}\n"

        return response

    async def get_response(
        self, query: QueryRequest
    ) -> AsyncGenerator[Union[PartialResponse, MetaResponse], None]:
        """
        Process the query and generate a response with weather information.

        Args:
            query: The query request from the user

        Yields:
            Response chunks as PartialResponse or MetaResponse objects
        """
        try:
            # Extract the query contents
            user_message: str = self._extract_message(query)

            # Log the extracted message
            logger.debug(f"[{self.bot_name}] Received message: {user_message}")

            # Add metadata about the bot if requested
            if user_message.lower().strip() == "bot info":
                metadata: Dict[str, Any] = self._get_bot_metadata()
                yield PartialResponse(text=json.dumps(metadata, indent=2))
                return

            message: str = user_message.strip()

            # Help command
            if message.lower() in ["help", "?", "/help"]:
                help_text: str = """
## 🌤️ Weather Bot

I can provide weather information for any location around the world.

Just type a city or location name, for example:
- `New York`
- `London, UK`
- `Tokyo`
- `Paris, France`

I'll give you the current weather conditions, temperature, and more.
"""
                yield PartialResponse(text=help_text)
                return

            # Empty query
            if not message:
                yield PartialResponse(
                    text="Please enter a location name. Type 'help' for instructions."
                )
                return

            # Check for specific commands/keywords
            if message.lower() in ["current location", "my location", "here"]:
                yield PartialResponse(
                    text="Please specify a location by name (e.g., 'New York', 'London, UK')."
                )
                return

            # Get weather data
            try:
                yield PartialResponse(text=f"Getting weather for {message}...\n\n")

                weather_data: WeatherData = await self._get_weather(message)
                formatted_weather: str = self._format_weather_data(weather_data)

                yield PartialResponse(text=formatted_weather)

            except BotErrorNoRetry as e:
                yield PartialResponse(text=f"Error: {str(e)}")
            except Exception as e:
                yield PartialResponse(text=f"Weather error: {str(e)}")
                return

        except Exception:
            # Let the parent class handle errors
            async for resp in super().get_response(query):
                yield resp
