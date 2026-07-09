from Expanse_Class import ExpenseDatabase


db = ExpenseDatabase()


# ----------------------------
# Categories
# ----------------------------

db.add_category(
    "groceries",
    "Food, supermarkets and everyday household supplies"
)

db.add_category(
    "lifestyle&fun",
    "Restaurants, hobbies, entertainment and leisure activities"
)

db.add_category(
    "mobility",
    "Public transport, fuel, taxis and transportation costs"
)

db.add_category(
    "family",
    "Children, childcare, school and family-related expenses"
)

db.add_category(
    "education",
    "Courses, books, training and learning expenses"
)

db.add_category(
    "healthcare",
    "Doctors, pharmacies, medication and medical services"
)

db.add_category(
    "subscriptions",
    "Recurring subscriptions such as Netflix, Spotify or software"
)

db.add_category(
    "fixed costs",
    "Rent, electricity, internet, insurance and recurring essential bills"
)


# ----------------------------
# Rule keywords
# ----------------------------

# groceries
for keyword in [
    "rewe",
    "aldi",
    "lidl",
    "edeka",
    "netto",
    "penny"
]:
    db.add_keyword(
        "groceries",
        keyword
    )


# mobility
for keyword in [
    "shell",
    "aral",
    "deutsche bahn",
    "db",
    "uber"
]:
    db.add_keyword(
        "mobility",
        keyword
    )


# subscriptions
for keyword in [
    "netflix",
    "spotify",
    "disney",
    "amazon prime"
]:
    db.add_keyword(
        "subscriptions",
        keyword
    )


# healthcare
for keyword in [
    "apotheke",
    "arzt",
    "pharmacy"
]:
    db.add_keyword(
        "healthcare",
        keyword
    )


db.close()

print("Database initialized successfully.")