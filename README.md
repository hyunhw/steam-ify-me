Steam-ify your DLC
==================

This [application](steam-ify.me) is a tool I developed to help game developers strategize expanding their game on Steam, a PC game platform, as a part of my Insight project.
The app takes a Steam user ID, desired stand-alone game to expand, and the expansion pack's price and release date as inputs and predicts whether or not the user will like the expansion-pack.

All data used in this application are scraped from the Steam web store using Scrapy, where the detailed documentation of the data-pipeline is shown in the iPython notebooks located in the folder `app/static/data`.
The application is hosted on AWS and uses the PostgreSQL database, which is hosted on Amazon RDS.
