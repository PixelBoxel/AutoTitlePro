from imdb import Cinemagoer
import sys

try:
    ia = Cinemagoer()
    print("Getting 'The Matrix' by ID (0133093)...")
    movie = ia.get_movie('0133093')
    print(f"Movie: {movie['title']} ({movie.get('year')})")
    
    print("Searching again...")
    results = ia.search_movie("The Matrix")
    print(f"Found {len(results)} results.")
except Exception as e:
    print(f"Error: {e}")
