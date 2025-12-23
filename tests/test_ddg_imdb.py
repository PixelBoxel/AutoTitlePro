from duckduckgo_search import DDGS
import re
from imdb import Cinemagoer

def get_imdb_id(query):
    print(f"Searching DDG for: {query}")
    try:
        with DDGS() as ddgs:
            # Search simpler
            print("Querying DDG...")
            results_gen = ddgs.text(f"{query} imdb", max_results=5)
            
            # Using list to force generator
            results = list(results_gen)
            print(f"Raw results count: {len(results)}")
            
            for r in results:
                url = r['href']
                print(f"Found URL: {url}")
                # logical pattern for tt + digits
                match = re.search(r'tt\d+', url)
                if match:
                    return match.group(0)
    except Exception as e:
        print(f"DDG Error: {e}")
    return None

ia = Cinemagoer()
def test_movie(name):
    print(f"\n--- Testing {name} ---")
    imdb_id = get_imdb_id(name)
    if imdb_id:
        print(f"Found ID: {imdb_id}")
        # Need to strip 'tt' for cinemagoer sometimes? usually it handles it.
        # cinemagoer expects just digits usually for get_movie!
        clean_id = imdb_id.replace('tt', '')
        print(f"Fetching metadata for ID: {clean_id}")
        try:
            movie = ia.get_movie(clean_id)
            print(f"Result: {movie['title']} ({movie.get('year')})")
        except Exception as e:
             print(f"Cinemagoer Error: {e}")
    else:
        print("No ID found.")

if __name__ == "__main__":
    test_movie("The Matrix 1999")
    test_movie("Breaking Bad")
