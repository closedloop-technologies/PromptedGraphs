import asyncio

from promptedgraphs.config import Config, load_config
from promptedgraphs.extraction.entities_from_text import entities_from_text


async def main():
    load_config()

    travel_text = """Hello fellow travelers! We're venturing to New Zealand from March 5-18th as a couple. We'll primarily be in Auckland visiting my sister, but we're hoping to explore more of the North Island. Since we're big fans of adventure sports and nature, we're thinking of places like the Tongariro Alpine Crossing or maybe Waitomo Caves. However, we're unsure about the best routes or if there are any hidden gems nearby. Any tips or suggestions? Has anyone been around those areas in March? Recommendations for cozy accommodations, local eateries, or any must-visit spots around Auckland would be greatly appreciated. Cheers!"""
    itinerary_entities = {
        "TRAVELER": "List of travelers with their ages and relationship details.",
        "DATE": "Absolute or relative dates or periods",
        "DEPARTURE LOCATION": "Location from where the travelers will start their journey.",
        "LOCATIONS": "All destinations and places mentioned in the travel request.",
        "ACCOMODATIONS": "Details of hotels and other lodging options mentioned.",
        "ACTIVITIES": "List of activities and attractions highlighted in the travel plan.",
        "NEEDS": "Special requirements such as accessibility, dietary needs, or medical considerations.",
        "INTERESTS": "Additional activities or attractions the travelers might enjoy.",
    }

    async for msg in entities_from_text(
        travel_text, labels=itinerary_entities, config=Config(), include_reason=True
    ):
        print(msg)


if __name__ == "__main__":
    asyncio.run(main())
