import streamlit as st
import pandas as pd
import pickle
import requests
import os
# from dotenv import load_dotenv
import concurrent.futures

# -- loading api key and setting up the page --
# i put the key in a .env file so i don't accidentally push it to github
tmdb_api_key = st.secrets["TMDB_API_KEY"]

st.set_page_config(
    page_title="Cinematch - Find Movies",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -- styling and css stuff --
# found this cool background image on unsplash
bg_img_url = "https://images.unsplash.com/photo-1489599849927-2ee91e4543e3?q=80&w=2072&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"

def inject_css():
    # this is all my custom css to make it look better
    # a lot of this was trial and error
    the_css = f"""
    <style>
        /* --- google fonts --- */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&family=Roboto:wght@400;500&display=swap');

        /* --- main app background --- */
        .stApp {{
            background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url({bg_img_url});
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        /* --- text styles --- */
        body, .stApp, .stButton>button, .stSelectbox [data-baseweb="select"] {{
            font-family: 'Roboto', sans-serif;
            color: #E0E0E0;
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Montserrat', sans-serif;
            color: #FFFFFF;
            font-weight: 700;
        }}

        h1 {{
            color: #E50914; /* netflix red is cool */
        }}
        
        .stMarkdown p {{
            font-size: 1.1rem;
        }}

        /* --- sidebar --- */
        [data-testid="stSidebar"] {{
            background-color: rgba(15, 15, 15, 0.85);
            backdrop-filter: blur(5px);
            border-right: 1px solid #E50914;
        }}
        [data-testid="stSidebar"] h1 {{
            font-size: 2.5rem;
        }}

        /* --- widgets like buttons and selectbox --- */
        .stButton>button {{
            border: 2px solid #E50914;
            background-color: transparent;
            color: #E50914;
            padding: 8px 5px; 
            border-radius: 8px;
            transition: all 0.3s ease-in-out;
            font-weight: 600;
            line-height: 1.3; 
            text-align: center; 
            height: 4.5em; /* fixed height for the two-line button */
        }}
        .stButton>button:hover {{
            background-color: #E50914;
            color: #FFFFFF;
            border-color: #E50914;
        }}
        .stButton>button:focus {{
             box-shadow: 0 0 0 2px #E50914 !important;
             border-color: #E50914 !important;
        }}
        
        .stSelectbox [data-baseweb="select"] > div {{
            background-color: #333;
            border-color: #555;
            color: #E0E0E0;
        }}
        
        [data-testid="stMetric"] {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }}
        
        
        
        /* --- finally got the recommendation cards to look right --- */
        [data-testid="stHorizontalBlock"] > div {{
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
            background-color: rgba(30, 30, 30, 0.7);
            border-radius: 10px;
            padding: 1rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            text-align: center;
            border: 1px solid #444;
        }}
        [data-testid="stHorizontalBlock"] > div:hover {{
            transform: translateY(-10px);
            box-shadow: 0 10px 20px rgba(229, 9, 20, 0.3);
            border-color: #E50914;
        }}
        .movie-title {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            line-height: 1.5em; 
            color: #FFFFFF;
            margin-top: 0.8rem;
            height: 3em; /* needs to be a fixed height for 2 lines */
            
            /* this is the magic for multi-line text with ... */
            display: -webkit-box;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 2; 
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .movie-caption {{
            font-size: 0.9rem;
            color: #AAAAAA;
        }}
        
        /* --- placeholder for posters that dont load --- */
        .poster-placeholder {{
            aspect-ratio: 2 / 3; 
            width: 100%;
            background-color: #181818; 
            border: 1px dashed #444; 
            border-radius: 7px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 1rem;
            box-sizing: border-box; 
        }}
        .poster-placeholder-text {{
            color: #777; 
            font-style: italic;
            font-size: 0.9rem;
        }}
        
    </style>
    """
    st.markdown(the_css, unsafe_allow_html=True)

# -- data loading and processing functions --

@st.cache_resource
def load_data_files():
    # this loads the big pickle file with the model and data
    try:
        with open('recommender.pkl', 'rb') as f:
            pickle_data = pickle.load(f)
        return pickle_data
    except FileNotFoundError:
        st.error("ERROR: recommender.pkl not found. Make sure it's in the same folder as the script.")
        st.stop()
    except Exception as e:
        st.error(f"Something went wrong loading the pickle file: {e}")
        st.stop()

@st.cache_data(show_spinner=False)
def get_movie_info_from_api(title):
    # fetches stuff like posters and ratings from TMDB
    fallback_poster = "https://via.placeholder.com/500x750?text=Poster+Not+Available"
    try:
        # first try searching with the exact title
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={requests.utils.quote(title)}"
        res = requests.get(url, timeout=10)
        res.raise_for_status() # this will error if the request fails
        api_results = res.json().get('results', [])

        # if that fails, try cleaning the title up (e.g., remove year)
        if not api_results:
            clean_title = ''.join([c for c in title if c.isalpha() or c.isspace()]).strip()
            if clean_title and clean_title != title:
                url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={requests.utils.quote(clean_title)}"
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                api_results = res.json().get('results', [])
            if not api_results:
                return {"poster_url": fallback_poster, "error": f"Couldn't find '{title}' on TMDB."}

        # get the details for the best match (the first result)
        best_match = api_results[0]
        movie_id = best_match.get('id')
        if not movie_id:
            return {"poster_url": fallback_poster, "error": "API found a match but no movie ID."}

        detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb_api_key}"
        detail_res = requests.get(detail_url, timeout=10)
        detail_res.raise_for_status()
        details_json = detail_res.json()

        # return a dictionary with all the info
        return {
            "poster_url": f"https://image.tmdb.org/t/p/w500/{details_json.get('poster_path')}" if details_json.get('poster_path') else fallback_poster,
            "tagline": details_json.get('tagline', ''),
            "tmdb_url": f"https://www.themoviedb.org/movie/{movie_id}",
            "release_date": details_json.get('release_date', ''),
            "vote_average": details_json.get('vote_average', None),
            "overview": details_json.get('overview', '')
        }
    except requests.exceptions.RequestException as e:
        return {"poster_url": fallback_poster, "error": f"API request failed: {e}"}

# Just replace the old find_similar_movies function with this one

@st.cache_data(show_spinner=False)
def find_similar_movies(movie_title, num_recs=5):
    # this is the core recommender logic using the nearest neighbors model
    main_data = load_data_files()
    if movie_title not in main_data['indices']:
        st.warning(f"'{movie_title}' is not in my database. Try another one.")
        return pd.DataFrame()
    
    # --- FIX IS HERE ---
    # okay so sometimes a movie title is in the data more than once, which gives a series of indices
    # instead of just one number. this was causing the "ambiguous value" crash.
    potential_indices = main_data['indices'][movie_title]
    if isinstance(potential_indices, pd.Series):
        # if it's a series, just grab the first one. problem solved.
        idx = potential_indices.iloc[0]
    else:
        # otherwise, it was just a single number, so we're good.
        idx = potential_indices
    # --- END OF FIX ---

    # just in case the index is somehow out of bounds
    if idx >= main_data['tfidf_matrix'].shape[0]:
        st.error(f"Data is messed up for '{movie_title}'. Pick another movie.")
        return pd.DataFrame()

    distances, indices = main_data['nn_model'].kneighbors(
        main_data['tfidf_matrix'][idx], n_neighbors=num_recs + 1
    )
    # the first result is the movie itself, so we skip it
    movie_indices = indices[0][1:]
    return main_data['df'].iloc[movie_indices]

@st.cache_data(show_spinner=False)
def get_all_details_fast(titles):
    # learned about this in my networks class, it's way faster than a normal loop
    # uses threads to make all the api calls at the same time
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(get_movie_info_from_api, titles))
    return results

# -- session state and callbacks --
# this stuff keeps track of the selected movie and history
if 'selected_movie' not in st.session_state:
    st.session_state.selected_movie = ""
if 'recommendation_history' not in st.session_state:
    st.session_state.recommendation_history = []

# this runs when you pick a movie from the dropdown
def on_movie_select():
    movie_title = st.session_state.movie_selector
    if movie_title:
        st.session_state.selected_movie = movie_title
        if not st.session_state.recommendation_history or st.session_state.recommendation_history[-1] != movie_title:
            st.session_state.recommendation_history.append(movie_title)

def reset_everything():
    st.session_state.selected_movie = ""
    st.session_state.recommendation_history = []

# this runs when you click a button on a recommended movie card
def pick_movie_from_rec(title):
    st.session_state.selected_movie = title
    if not st.session_state.recommendation_history or st.session_state.recommendation_history[-1] != title:
        st.session_state.recommendation_history.append(title)

# -- main app starts here --

# check for api key first
if not tmdb_api_key:
    st.error("FATAL ERROR: TMDB_API_KEY is missing. You need to create a .env file with the key.")
    st.stop()

movie_data = load_data_files()
# add an empty option to the start of the list for the placeholder text
movie_titles_list = [""] + sorted(movie_data['df']['title'].drop_duplicates().tolist())

inject_css()

# -- the sidebar --
with st.sidebar:
    st.title("🎬 Cinematch")
    st.markdown("### *Your AI Movie Curator*")
    
    # this makes sure the selectbox updates when a movie is picked from a card
    try:
        selected_idx = movie_titles_list.index(st.session_state.selected_movie)
    except ValueError:
        selected_idx = 0

    st.selectbox(
        "Select a Movie to Start",
        options=movie_titles_list,
        key='movie_selector', # this key is just for the widget
        index=selected_idx,
        on_change=on_movie_select,
        format_func=lambda x: 'Select a movie...' if x == "" else x
    )

    st.divider()
    st.header("Discovery History")
    if st.session_state.recommendation_history:
        # show history in reverse order (newest first)
        for idx, movie in enumerate(reversed(st.session_state.recommendation_history)):
            st.button(movie, use_container_width=True, key=f"hist_{idx}_{movie}", on_click=pick_movie_from_rec, args=(movie,))
        
        st.divider()
        st.button("Clear History & Selection", on_click=reset_everything, use_container_width=True)
    else:
        st.info("Your viewed movies will appear here.")
        
    st.markdown("---")
    with st.expander("ℹ️ About This Project", expanded=False):
        st.markdown("""
            This uses **Content-Based Filtering**. It looks at stuff like genre, director, and keywords to find movies that are alike.
            
            **Project by:** Muhammad Tahir
            - [LinkedIn](https://www.linkedin.com/in/muhammad-tahir-data/)
            - [GitHub](https://github.com/mtahir-ds/)
        """)

# -- the main page content --
if not st.session_state.selected_movie:
    # this is the welcome screen
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("# Welcome to **Cinematch**", unsafe_allow_html=True)
    st.markdown("##### Discover your next favorite movie with the power of AI.")
    st.info("👈 **Select a movie from the sidebar to get started!**")
else:
    # this shows when a movie has been selected
    selected_movie_title = st.session_state.selected_movie
    st.header(f"You Selected: {selected_movie_title}")
    
    with st.spinner("Getting movie details..."):
        selected_movie_row = movie_data['df'][movie_data['df']['title'] == selected_movie_title].iloc[0]
        api_data = get_movie_info_from_api(selected_movie_title)

    if 'error' in api_data:
        st.toast(api_data['error'], icon="🚨")

    main_col1, main_col2 = st.columns([1, 2], gap="large")
    with main_col1:
        # show my custom placeholder if the poster is missing
        poster_url = api_data.get('poster_url')
        if "via.placeholder.com" in poster_url:
            st.markdown(
                f'<div class="poster-placeholder"><span class="poster-placeholder-text">{selected_movie_title}</span></div>',
                unsafe_allow_html=True
            )
        else:
            st.image(poster_url, use_container_width=True)

        if api_data.get('tmdb_url'):
            st.link_button("View on TMDB ↗", api_data.get('tmdb_url'), use_container_width=True)

    with main_col2:
        tagline = api_data.get('tagline')
        if tagline:
            st.markdown(f"> ### *{tagline}*")

        st.subheader("Overview")
        # use api overview first, but fall back to my dataset's overview
        overview = api_data.get('overview', selected_movie_row.get('overview', 'No overview available.'))
        st.write(overview if isinstance(overview, str) and overview.strip() else "No overview available for this movie.")

        metric_col1, metric_col2 = st.columns(2)
        
        rating_val = api_data.get('vote_average', selected_movie_row['vote_average'])
        display_rating = f"{rating_val:.1f} / 10" if rating_val and rating_val > 0 else "N/A"
        metric_col1.metric(label="Rating ⭐", value=display_rating)

        try:
            release_date = api_data.get('release_date', selected_movie_row['release_date'])
            year = pd.to_datetime(release_date).year if release_date else "N/A"
            metric_col2.metric(label="Year 🗓️", value=str(year))
        except (ValueError, TypeError):
            metric_col2.metric(label="Year 🗓️", value="N/A")

        st.write(f"**Director:** {selected_movie_row['director'].title().replace(',', ', ')}")
        st.write(f"**Genres:** {', '.join([g.title() for g in selected_movie_row['genres']])}")

    # -- recommendations section --
    st.divider()
    st.header(f"Because you liked {selected_movie_title}...")

    # this one spinner runs while all the API calls happen in the background
    with st.spinner('Thinking of some recommendations...'):
        recs_df = find_similar_movies(selected_movie_title, num_recs=5)
        recs_df = recs_df.drop_duplicates(subset=['title'])
        if not recs_df.empty:
            titles_to_fetch = recs_df['title'].tolist()
            all_api_details = get_all_details_fast(titles_to_fetch)

    if not recs_df.empty:
        cols = st.columns(5, gap="medium")
        # now loop through the results and show the cards
        for i, row in enumerate(recs_df.itertuples()):
            with cols[i]:
                current_rec_details = all_api_details[i] 

                poster_url = current_rec_details.get('poster_url')
                
                if "via.placeholder.com" in poster_url:
                    st.markdown(
                        f'<div class="poster-placeholder"><span class="poster-placeholder-text">{row.title}</span></div>', 
                        unsafe_allow_html=True
                    )
                else:
                    st.image(poster_url, use_container_width=True)

                # make title safe for html just in case
                safe_title_for_html = row.title.replace("'", "'").replace('"', '"')
                
                st.markdown(
                    f"<p class='movie-title' title='{safe_title_for_html}'>{row.title}</p>", 
                    unsafe_allow_html=True
                )
                
                try:
                    rec_year = pd.to_datetime(row.release_date).year
                    rec_rating = current_rec_details.get('vote_average', row.vote_average)

                    if rec_rating and rec_rating > 0:
                        caption = f"⭐ {rec_rating:.1f} | {rec_year}"
                    else:
                        caption = f"🗓️ {rec_year}"
                    
                    st.markdown(f"<p class='movie-caption'>{caption}</p>", unsafe_allow_html=True)

                except (ValueError, TypeError):
                    st.markdown(f"<p class='movie-caption'> </p>", unsafe_allow_html=True) # empty space to keep alignment
                
                st.button(
                    "Recommend\nfrom this", 
                    key=f"rec_{row.Index}", 
                    on_click=pick_movie_from_rec, 
                    args=(row.title,),
                    use_container_width=True
                )
    else:
        # only show this error if a movie is actually selected
        if st.session_state.selected_movie: 
            st.error("Damn, couldn't find any good recommendations for that one in my database.")
