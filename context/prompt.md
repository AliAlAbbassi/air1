alright now I'd like to create a workflow that'll search for people using the search api and save these profiles to be used for outreach later

here's the url 

https://www.linkedin.com/search/results/people/?keywords=technical%20recruiter&origin=SWITCH_SEARCH_VERTICAL

use the existing tables and service functions that we have

there should be a param in the workflow that'll set the number of pages we want to get from the search results

then create another workflow that'll send connection requests to the list we just fetched with the help of the previous workflow we created, and make sure these connection requests are tracked, ie we don't send a connection request to lead that we have connected with in the past 