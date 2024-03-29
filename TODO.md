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
- Make repo public
- Deploying it
  - Setup subdomain
  - Deploy it to VPS
  - Set up prometheus scraping
  - Set up grafana alerts if data fetcher lag too big
  - Test out example feed
    - Test 1: Set up a feed in feed readers on FAExport, then redirect those RSS requests to FA-RSS, observe result
      - Results [RSSTT]: Old submissions from the bottom of the feed got posted as new items, as FA-RSS feeds are longer
      - Results [Podcast Addict]: Old submissions from the bottom of the feed are added as unread items at the bottom of the feed
      - Results [Feedly]: Old submissions did not appear in feed at all
    - Test 2: Create a new feed of an uninitialized user, see if the reader accepts the preview descriptions and pub dates, then updates with full descriptions later
      - Results [Podcast Addict]: Old descriptions and pub dates remain, unless feed is reset
      - Results [RSSTT]: Initial items are not posted, no sign of reposting when feed is updated
  - Leave it running for a while to populate data and back cache

## Todo
- Deploy it
  - Pre-populate all feeds currently being requested from FAExport
  - Change nginx rules to send all gallery.rss and scraps.rss requests to FA RSS
- Write some automated system tests
  - Ensure feed URLs all return valid responses
  - Ensure feed responses are valid RSS?
  - Ensure new user triggers task?
    - Ensure you get a mix of completed and preview items?
  - Ensure usernames are case insensitive
  - Ensure usernames with weird characters are handled
- Test that asyncio.gather(API.get_submission()) actually obeys rate limit properly?
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
