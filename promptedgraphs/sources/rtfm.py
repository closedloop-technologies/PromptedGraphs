"""Sometimes you just have to RTFM.
Occationally documentation contains links that are helpful to understand the APIs and usage.

This module contains functions to help you bootstrap a datagraph from APIs and functions.

In particular, given a url

 * renders the webpage (or portion of the webpage) with javascript enabled
 * formats the webpage as markdown
"""

import os
from urllib.parse import quote

import requests

from promptedgraphs.config import Config


class OGTags:
    def __init__(self, token: str = None, config: Config = None):
        if token:
            self.token = token
        elif config:
            self.token = config.ogtags_api_key
        else:
            self.token = os.environ.get("OGTAGS_API_KEY")
        assert (
            self.token
        ), "You must provide an API token to use OGTags, set OGTAGS_API_KEY in your environment"

    def get_page_source_via_chrome_render(self, crawl_url):
        encoded_url = quote(crawl_url, safe="")
        full_url = f"https://api.ogtags.dev/v1/page-source/chrome-render/{encoded_url}"

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        params = {"width": "1200", "height": "630"}
        response = requests.get(full_url, headers=headers, params=params)

        if response.status_code != 200:
            raise RuntimeError(
                f"Request to OGTags failed with status code {response.status_code} and message {response.text}"
            )

        return response.text


def fetch_from_ogtags(crawl_url):
    ogtags = OGTags()
    return ogtags.get_page_source_via_chrome_render(crawl_url)


if __name__ == "__main__":
    # Example usage:
    crawl_url = (
        "https://developers.google.com/places/web-service/search#FindPlaceRequests"
    )
    result = fetch_from_ogtags(crawl_url)
    print(result)
