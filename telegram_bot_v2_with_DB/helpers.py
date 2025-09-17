from io import BytesIO

def pil_to_bytes(pil_image):
    print("Helpers: Converting PIL image to bytes")
    byte_io = BytesIO()
    pil_image.convert("RGB").save(byte_io, format="JPEG")
    byte_io.seek(0)
    return byte_io


async def get_best_urls(face_check_results):
    best_urls_list = []
    print(f"total urls found: {len(face_check_results)}")

    for link in face_check_results:
        if link["score"] >= 80:
            best_urls_list.append((link["score"], link["url"]))
            if len(best_urls_list) >= 8:
                break

    if len(best_urls_list) == 0:
        print("NO urls found")
        
    print(f"selected urls number: {len(best_urls_list)}")
    return best_urls_list