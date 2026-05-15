import os

def list_known_people_with_photos():
    known_dir = os.path.join(BASE_DIR, "known")
    items = []
    for person in list_known_people():
        person_dir = os.path.join(known_dir, person)
        files = iter_image_files(person_dir) if os.path.isdir(person_dir) else []
        items.append({
            "name": person,
            "count": len(files),
            "preview": files[0] if files else None,
        })
    return items
# ---- Helpers: bekende personen uit known/*.npz ----
def list_known_people():
    known_dir = os.path.join(BASE_DIR, "known")
    people = []
    for fn in os.listdir(known_dir):
        if fn.lower().endswith(".npz"):
            people.append(os.path.splitext(fn)[0])
    people.sort(key=lambda s: s.lower())
    return people
