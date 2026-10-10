from PIL import Image, ImageDraw

img = Image.open('standing.png').convert('RGBA')
width, height = img.size

# Flood fill outer black borders from all four corners
ImageDraw.floodfill(img, (0, 0), (0, 0, 0, 0), thresh=35)
ImageDraw.floodfill(img, (width - 1, 0), (0, 0, 0, 0), thresh=35)
ImageDraw.floodfill(img, (0, height - 1), (0, 0, 0, 0), thresh=35)
ImageDraw.floodfill(img, (width - 1, height - 1), (0, 0, 0, 0), thresh=35)

img.save('cat_standing.png', 'PNG')
print('cat_standing.png created successfully with solid eyes!')
