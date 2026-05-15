import os

def iter_image_files(dir_path):
    if not os.path.isdir(dir_path):
        return
    for fn in os.listdir(dir_path):
        if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
            yield os.path.join(dir_path, fn)

def list_known_people_with_photos(known_dir: str):
    items = []
    for person in list_known_people(known_dir):
        person_dir = os.path.join(known_dir, person)
        files = list(iter_image_files(person_dir)) if os.path.isdir(person_dir) else []
        items.append({
            "name": person,
            "count": len(files),
            "preview": os.path.basename(files[0]) if files else None,
        })
    return items
# ---- Helpers: bekende personen uit known/*.npz ----
def list_known_people(known_dir: str):
    people = []
    for fn in os.listdir(known_dir):
        if fn.lower().endswith(".npz"):
            people.append(os.path.splitext(fn)[0])
    people.sort(key=lambda s: s.lower())
    return people
