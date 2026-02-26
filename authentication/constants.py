PRIMARY_GENRE_CHOICES = [
    ("romance", "Romance"),
    ("mystery_thriller", "Mystery / Thriller"),
    ("science_fiction", "Science Fiction"),
    ("fantasy", "Fantasy"),
    ("young_adult", "Young Adult"),
    ("childrens", "Children’s Books"),
    ("horror", "Horror"),
    ("literary", "Literary Fiction"),
    ("womens_fiction", "Women’s Fiction"),
    ("nonfiction", "Nonfiction"),
    ("action_adventure", "Action / Adventure"),
    ("comics_graphic", "Comics & Graphic Novels"),
]

AUDIENCE_TAG_CHOICES = [
    ("clean", "Clean / Sweet"),
    ("steamy", "Steamy"),
    ("explicit", "Explicit"),
    ("cozy", "Cozy"),
    ("dark", "Dark"),
    ("humor", "Humor-Forward"),
    ("faith", "Faith-Based / Christian"),
    ("holiday", "Holiday / Seasonal"),
    ("lgbtq", "LGBTQ+"),
    ("diverse", "Diverse / Inclusive"),
    ("series", "Series"),
    ("standalone", "Standalone"),
    ("short_reads", "Short Reads / Novellas"),
]

COLLABORATION_STATUS = [
    ("open to swap", "Open to Swaps"),
    ("invite only", "Invite Only"),
]

# Subgenre choices organized by primary genre
ROMANCE_SUBGENRES = [
    ('contemporary', 'Contemporary'),
    ('romantic_comedy', 'Romantic Comedy'),
    ('small_town', 'Small Town'),
    ('sports', 'Sports'),
    ('billionaire', 'Billionaire'),
    ('bad_boy', 'Bad Boy'),
    ('new_adult', 'New Adult'),
    ('erotic', 'Erotic'),
    ('reverse_harem', 'Reverse Harem'),
    ('paranormal', 'Paranormal'),
    ('romantic_suspense', 'Romantic Suspense'),
    ('dark_romance', 'Dark Romance'),
    ('historical', 'Historical'),
    ('western', 'Western'),
    ('military', 'Military'),
    ('medical', 'Medical'),
    ('holiday', 'Holiday'),
    ('sci_fi', 'Sci-Fi'),
    ('fantasy', 'Fantasy'),
    ('lgbtq', 'LGBTQ+'),
    ('mafia', 'Mafia'),
]

MYSTERY_THRILLER_SUBGENRES = [
    ('cozy', 'Cozy'),
    ('amateur_sleuth', 'Amateur Sleuth'),
    ('police_procedural', 'Police Procedural'),
    ('crime_thriller', 'Crime Thriller'),
    ('psychological_thriller', 'Psychological Thriller'),
    ('legal_thriller', 'Legal Thriller'),
    ('techno_thriller', 'Techno-Thriller'),
    ('suspense', 'Suspense'),
    ('historical', 'Historical'),
]

SCIENCE_FICTION_SUBGENRES = [
    ('space_opera', 'Space Opera'),
    ('military_sci_fi', 'Military Sci-Fi'),
    ('dystopian', 'Dystopian'),
    ('post_apocalyptic', 'Post-Apocalyptic'),
    ('time_travel', 'Time Travel'),
    ('hard_sci_fi', 'Hard Sci-Fi'),
    ('alien_first_contact', 'Alien / First Contact'),
    ('cyberpunk', 'Cyberpunk'),
]

FANTASY_SUBGENRES = [
    ('epic', 'Epic / High Fantasy'),
    ('urban', 'Urban Fantasy'),
    ('dark', 'Dark Fantasy'),
    ('portal', 'Portal Fantasy'),
    ('sword_sorcery', 'Sword & Sorcery'),
    ('mythology_retellings', 'Mythology / Retellings'),
    ('litrpg_gamelit', 'LitRPG / GameLit'),
]

YOUNG_ADULT_SUBGENRES = [
    ('romance', 'Romance'),
    ('fantasy', 'Fantasy'),
    ('sci_fi', 'Sci-Fi'),
    ('contemporary', 'Contemporary'),
    ('mystery_thriller', 'Mystery / Thriller'),
    ('paranormal', 'Paranormal'),
]

CHILDRENS_SUBGENRES = [
    ('picture_books', 'Picture Books'),
    ('early_readers', 'Early Readers'),
    ('chapter_books', 'Chapter Books'),
    ('middle_grade', 'Middle Grade'),
    ('educational', 'Educational'),
    ('comics_graphic_novels', 'Comics & Graphic Novels'),
]

HORROR_SUBGENRES = [
    ('psychological', 'Psychological'),
    ('supernatural', 'Supernatural'),
    ('paranormal', 'Paranormal'),
    ('dark_fantasy', 'Dark Fantasy'),
    ('thriller', 'Thriller'),
]

LITERARY_FICTION_SUBGENRES = [
    ('contemporary', 'Contemporary'),
    ('historical', 'Historical'),
    ('experimental', 'Experimental'),
]

WOMENS_FICTION_SUBGENRES = [
    ('contemporary', 'Contemporary'),
    ('book_club', 'Book Club'),
    ('family_relationships', 'Family / Relationships'),
    ('emotional_dramatic', 'Emotional / Dramatic'),
]

NONFICTION_SUBGENRES = [
    ('memoir', 'Memoir / Biography'),
    ('self_help', 'Self-Help / Personal Development'),
    ('business', 'Business / Finance'),
    ('health', 'Health & Wellness'), 
    ('parenting', 'Parenting / Family'),
    ('faith', 'Faith / Spirituality'),
    ('education', 'Education'),
    ('writing_publishing', 'Writing / Publishing'),
]

ACTION_ADVENTURE_SUBGENRES = [
    ('military', 'Military / War'),
    ('espionage', 'Espionage'),
    ('survival', 'Survival'),
    ('adventure_thriller', 'Adventure Thriller'),
]

COMICS_GRAPHIC_NOVELS_SUBGENRES = [
    ('fiction', 'Fiction'),
    ('nonfiction', 'Nonfiction'),
    ('childrens', 'Children\'s'),
    ('manga', 'Manga'),
]

# Mapping of primary genres to their subgenres
GENRE_SUBGENRE_MAPPING = {
    'romance': ROMANCE_SUBGENRES,
    'mystery_thriller': MYSTERY_THRILLER_SUBGENRES,
    'science_fiction': SCIENCE_FICTION_SUBGENRES,
    'fantasy': FANTASY_SUBGENRES,
    'young_adult': YOUNG_ADULT_SUBGENRES,
    'childrens': CHILDRENS_SUBGENRES,
    'horror': HORROR_SUBGENRES,
    'literary': LITERARY_FICTION_SUBGENRES,
    'womens_fiction': WOMENS_FICTION_SUBGENRES,
    'nonfiction': NONFICTION_SUBGENRES,
    'action_adventure': ACTION_ADVENTURE_SUBGENRES,
    'comics_graphic': COMICS_GRAPHIC_NOVELS_SUBGENRES,
}

# All subgenres combined (for validation)
ALL_SUBGENRES = (
    ROMANCE_SUBGENRES + MYSTERY_THRILLER_SUBGENRES + SCIENCE_FICTION_SUBGENRES +
    FANTASY_SUBGENRES + YOUNG_ADULT_SUBGENRES + CHILDRENS_SUBGENRES + HORROR_SUBGENRES +
    LITERARY_FICTION_SUBGENRES + WOMENS_FICTION_SUBGENRES + NONFICTION_SUBGENRES +
    ACTION_ADVENTURE_SUBGENRES + COMICS_GRAPHIC_NOVELS_SUBGENRES
)
