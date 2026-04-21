from location import get_location
with open("description.txt", "r") as f:
    TEXT = f.read()
    
print(get_location(TEXT))