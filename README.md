# FA RSS

This is meant to be a drop-in replacement for the RSS feeds already available via the [FAExport](https://github.com/Deer-Spangle/FAExport) project.
In fact, I'm planning to eventually send rss requests directed towards that, at [the public endpoint](https://faexport.spangle.org.uk) to this project instead.

This should enable some additional flexibility, but mostly it's about performance. The RSS endpoints on FAExport are naively cached, which results in each RSS request meaning lots of requests are sent to FurAffinity. This then means that if any of those requests fail, the RSS endpoint returns an error page. That's not very reliable or helpful.
As a result, the RSS results on FAExport are cached for a rather long time, to try and manage that. That's not great for users.

Hopefully this solution should provide a cleaner and faster feed for users.

However, this comes with a couple drawbacks:
- The first request of a user's gallery feeds can take a while to populate, but future requests should be faster.
- There's no cache invalidation, so if a user deletes a submission, the RSS feed will still reference a deleted submission. If this proves to be a problem, it should be easily fixable, please raise an issue if so!
- The above also means that title, image, or description updates might not be tracked. Again, if this proves to be a problem, raise an issue and I can investigate improving it.
