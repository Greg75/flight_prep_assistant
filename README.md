# Flight Prep Assistant API
A Python FastAPI-based service to generate detailed flight briefings by aggregating 
airfield, weather, NOTAM, and aircraft data from external APIs.

## Overview
This project provides an API that integrates multiple external 
aviation data sources to generate structured flight briefings. 
It supports:
- Retrieving and combining airfield and weather data
- Constructing detailed models of departure and arrival airfields
- Producing a comprehensive briefing including aircraft information and recommendations
- Serving briefing data via REST endpoints
- Generating downloadable PDF reports of the briefings
- Monitoring briefing generation status

## Features
- API Clients: Generic clients for various aviation-related APIs (Airfield, Weather, NOTAM, Aircraft) configurable via environment variables.
- Data Models: Typed models representing airfields, runways, wind, frequencies, aircraft, and briefings.
- Builder Pattern: AirfieldModelBuilder aggregates data from multiple API sources into a unified AirfieldModel.
- Briefing Generation: BriefingGenerator constructs a full briefing by combining departure and arrival airfield models with aircraft data.
- FastAPI Endpoints:
  - GET / – Basic health/status check 
  - GET /ping – API health ping 
  - POST /generate – Generate a new briefing from input data 
  - GET /briefing/{briefing_id}/download – Download briefing PDF 
  - GET /briefing/{briefing_id}/status – Check briefing generation status

## Setup and Configuration
### Environment Variables
Set the following environment variables to configure API base URLs:
```
| Variable Name      | Description                  |
|--------------------|------------------------------|
| AIRFIELD_API_URL   | Base URL for Airfield API    |
| WEATHER_API_URL    | Base URL for Weather API     |
| NOTAM_API_URL      | Base URL for NOTAM API       |
| AIRCRAFT_API_URL   | Base URL for Aircraft API    |
```

Example .env:

```env
AIRFIELD_API_URL=https://api.airfield.example.com
WEATHER_API_URL=https://api.weather.example.com
NOTAM_API_URL=https://api.notam.example.com
AIRCRAFT_API_URL=https://api.aircraft.example.com
```

## Usage
### 1. Starting the API
Run the FastAPI server:
```bash
    uvicorn main:app --reload
```

### 2. Generate a Flight Briefing
Send a POST request to /generate with JSON input including aircraft, 
departure, and arrival details.

Example input:
```json
{
  "aircraft_data": { /* aircraft details */ },
  "departure_airfield": "KJFK",
  "arrival_airfield": "KLAX"
}
```
The response will contain a structured BriefingModel with combined 
airfield and weather data.

### 3. Download the Briefing as PDF
Use the briefing ID from the generation response and request:
```bash
    GET /briefing/{briefing_id}/download
```
This returns a PDF file of the briefing.

### 4. Check Briefing Status
Check generation status via:
```bash
GET /briefing/{briefing_id}/status
```

## Architecture Details
### API Clients
- ApiClient is a generic client that reads the base URL from 
environment variables and sends GET requests with query parameters.
- Supports flexible integration with various external services.

### AirfieldModelBuilder
- Aggregates data from multiple APIs (airfield data + weather data).
- Parses and structures runway, frequency, wind, elevation, temperature, and METAR/TAF data into a unified model.

### BriefingGenerator
- Coordinates building detailed departure and arrival airfield models.
- Combines aircraft data with these models.
- Provides a BriefingModel output including a default flight recommendation.

### FastAPI Endpoints
- Root and health check endpoints for API availability.
- /generate endpoint to produce briefings.
- /briefing/{id}/download for PDF generation with status tracking.
- /briefing/{id}/status to query progress state.

### Logging and Error Handling
- Logs informative messages on each API call, generation step, and download.
- Raises meaningful exceptions on missing environment variables, API failures, or invalid briefing IDs.

### Future Improvements
- Support asynchronous API calls for better performance.
- Expand briefing details with NOTAM and aircraft-specific advisories.
- Add authentication and user management.
- Enhance PDF formatting and customization.

## Dependencies
- Python 3.9+
- FastAPI
- Requests
- Pydantic
- Uvicorn (for development server)
- WeasyPrint

## License
Licence WIP.