# Meetup.mu Scraper

Small utility to make my life easier (supposedly). It fetches events from meetup.com for a few community groups (MSCC, Laravel, NUGM, PYMUG) and throws the details into a database for [meetup.mu](https://meetup.mu) to read from.
So that I don't have to update events manually.




## ToDo

There's still a lot to be done. And I'm adding a ToDo which I will hopefully keep updated in the off-chance someone decides they want to contribute (please, PRs welcome <3)

- Database functionalities - add to DB if non-existent. Update DB if already present (check with URL as key)


## Deploy

```
docker build . -t registry.alexbissessur.dev/meetup-scraper:{} && docker push registry.alexbissessur.dev/meetup-scraper:{}
```
