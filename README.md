# Meetup.mu Scraper

Small utility to make my life easier (supposedly). It fetches events from meetup.com for a few community groups (MSCC, Laravel, NUGM, PYMUG) and throws the details into a database for [meetup.mu](https://meetup.mu) to read from.
So that I don't have to update events manually.


## ToDo

Nothing left to be done, this is pretty complete!

## Deploy

```
docker build . -f job.Dockerfile -t registry.alexbissessur.dev/meetup-scraper:{} && docker push registry.alexbissessur.dev/meetup-scraper:{}

docker build . -f api.Dockerfile -t registry.alexbissessur.dev/meetup-scraper-api:{} && docker push registry.alexbissessur.dev/meetup-scraper-api:{}
```
