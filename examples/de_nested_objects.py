import asyncio

from pydantic import BaseModel, Field

from promptedgraphs.config import Config, load_config
from promptedgraphs.data_extraction import extract_data


class Traveler(BaseModel):
    name: str = Field(title="Traveler Name")
    age: int | None = Field(None, title="Age of Traveler")
    relationship: str | None = Field(None, title="Relationship with other travelers")


class WorkflowState(BaseModel):
    """Defines the workflow state types for the AI Agent."""

    travelers: list[Traveler] = Field(
        title="TRAVELERS",
        description="A list of who is traveling, their ages, and relationships between each other",
    )
    departure_date: str | None = Field(title="Departure Date")
    return_date: str | None = Field(title="Return Date")
    expected_length_of_trip: str | None = Field(title="Expected Length of Trip")
    departure_location: str | None = Field(
        title="DEPARTURE LOCATION", description="Where the travelers are departing from"
    )
    budget: str | None = Field(
        title="BUDGET",
        description="Any information related to the expected costs or budget limitations for the trip",
    )
    trip_reason: str | None = Field(
        title="TRIP REASON",
        description="The purpose of the trip, e.g., fun, work, etc.",
    )
    locations: list[str] | None = Field(
        title="LOCATIONS",
        description="A list of all locations mentioned in the request",
    )
    accomodations: list[str] | None = Field(
        title="ACCOMODATIONS",
        description="A list of all hotels and other accommodations mentioned in the request",
    )
    activities: list[str] | None = Field(
        title="ACTIVITIES",
        description="A list of all activities and travel interests mentioned in the request",
    )
    needs: str | None = Field(
        title="NEEDS",
        description="Accessibility, dietary restrictions, or medical considerations",
    )
    accomodation_preferences: str | None = Field(
        title="ACCOMODATION PREFERENCES",
        description="Preference for types of lodging such as hotels, Airbnbs, or opinions on places to stay",
    )
    transportation_preferences: str | None = Field(
        title="TRANSPORTATION PREFERENCES",
        description="Any preference related to how they like to travel between destinations and generally on the trip",
    )
    interests: list[str] | None = Field(
        title="INTERESTS",
        description="Other interests mentioned that the travelers would likely enjoy doing",
    )


async def main():
    load_config()

    msg = """Message from Jane, Hello fellow travelers! We're venturing to New Zealand from March 5-18th as a couple. We'll primarily be in Auckland visiting my sister, but we're hoping to explore more of the North Island. Since we're big fans of adventure sports and nature, we're thinking of places like the Tongariro Alpine Crossing or maybe Waitomo Caves. However, we're unsure about the best routes or if there are any hidden gems nearby. Any tips or suggestions? Has anyone been around those areas in March? Recommendations for cozy accommodations, local eateries, or any must-visit spots around Auckland would be greatly appreciated. Cheers!"""

    async for state in extract_data(
        text=msg, output_type=WorkflowState, config=Config()
    ):
        print(state)


if __name__ == "__main__":
    asyncio.run(main())
