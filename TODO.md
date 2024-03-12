# Todo

## Done
- Ensure database stuff works
- Build RSS feed
- Add gallery/scraps value to FAExport
- Build gallery list from database
- Data Fetcher, populating database with all new posts
- Handle 404 errors and such from API
- Dockerfile
- Prometheus metrics
- Fix logging
- Handle slowdown state from API
- Readme
- Homepage
- Browse endpoint
- Return RSS feed preview on first fetch (for speed)
  - Then remove the slow comment from readme

## Todo
- Deploy it
  - Setup subdomain
  - Deploy it to VPS
  - Set up prometheus scraping
  - Set up grafana alerts if data fetcher lag too big
  - Leave it running for a while to populate data and back cache
  - Test out an example feed
    - Create one test feed on FAExport in an RSS reader
    - Set nginx to forward that one feed endpoint to FA RSS instead of FAExport
  - Pre-populate all feeds currently being requested from FAExport
  - Change nginx rules to send all gallery.rss and scraps.rss requests to FA RSS

- Make repo public
- Publish docker images


## Stretch goals
- Favourites endpoint
- Auth endpoints
  - Auth via get params maybe? 
  - Submissions endpoint
- Maybe journals endpoint?
- DB connectionpool?
- Speed up data fetcher with concurrent data fetcher workers

## Potential future expansion
- Store more post metadata?
- Ability to swap links for substitute domain? (fxraffinity)
- FAExport common client with error handling and object models

## Out of scope
- Sharing data with FASearchBot
