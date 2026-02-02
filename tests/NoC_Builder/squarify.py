# INPUTS
dimx = 6
dimy = 4
IIs = 1
IMs = 2

# FIXED
area_IM = 4
global_tiles_location = []

def width(dimx, dimy):
    return min(dimx, dimy)

def worst(row, w):
    if(row == []):
        return float('inf')
    
    else:
        s       = sum(row)
        rmax    = max(row)
        rmin    = min(row)

        # Cost function --> Aspect Ratio
        term1   = (rmax * w**2) / (s**2)   # w_r/h; h = s/w; w_r = r/h
        term2   = (s**2) / (rmin * w**2)   # h/w_r;

        return max(term1, term2)

def squarify(children, row, w, coord, dims):
    if len(children) == 0:
        if(len(row) == 0):
            return
        else:
            layoutrow(row, coord, dims, w)
            return
    
    c = children[0]
    if worst(row, w) >= worst(row + [c], w):
        squarify(children[1:], row + [c], w, coord, dims)
    else:
        new_dims, new_coord = layoutrow(row, coord, dims, w)
        newx, newy = new_dims
        squarify(children, [], width(newx, newy), new_coord, new_dims)

def tetris_make_tiles():
    area = dimx * dimy
    area_II     = (area - IMs * area_IM) / IIs
    II_queue    = [area_II for _ in range(IIs)]
    IM_queue    = [area_IM for _ in range(IMs)]
    # input_queue = II_queue + IM_queue
    input_queue = II_queue + IM_queue
    start_coord  = (0, 0)
    input_dims  = (dimx, dimy)
    print("------Areas-----")
    print(area_II, area_IM)
    squarify(input_queue, [], width(dimx, dimy), start_coord, input_dims)
    print(global_tiles_location)

def layoutrow(row, coord, dim, w):
    global global_tiles_location
    x,y = coord
    dx, dy = dim

    s = sum(row)
    h = s/w
    w_r = [r/h for r in row]

    new_coord   = (0,0)
    new_dim     = (0,0)
    tiles = []

    if dx == w:
        print("Horizontal stack")
        # dy = dy - h
        new_dim     = (dx, dy-h)
        new_coord   = (x, y+h)
        
        # Save coordinates
        for dX in w_r:
            tiles.append([(x,y), (x+dX-1, y+h-1)])
            x = x + dX

    else:
        print("Vertical Stack")
        # dx = dx - h
        new_dim     = (dx-h, dy)
        new_coord   = (x+h, y)

        # Save coordinates
        for dY in w_r:
            tiles.append([(x,y), (x+h-1, y+dY-1)])
            y = y + dY
    
    global_tiles_location += tiles
    return [new_dim, new_coord]

def print_tiles():
    # 1. Map every (x, y) coordinate to a Tile ID
    grid_map = {}
    tiles = global_tiles_location
    
    # Use letters (A, B, C...) for clearer visualization than numbers
    ids = [chr(65 + i) for i in range(len(tiles))] 
    
    for i, tile in enumerate(tiles):
        (x1, y1), (x2, y2) = tile
        # Convert floats to integers for grid mapping
        x1, y1 = int(x1), int(y1)
        x2, y2 = int(x2), int(y2)
        
        # Mark the grid cells belonging to this tile
        # Note: Your layout logic uses inclusive-inclusive range logic (x to x+w-1)
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                grid_map[(x, y)] = ids[i]

    print("\n[ VISUALIZATION ]")
    print(f"Canvas: {dimx}x{dimy}\n")

    # 2. Print Top Border
    print("+" + "---+" * dimx)

    # 3. Iterate through rows
    for y in range(dimy):
        # --- Print Content Line ---
        row_str = "|"
        for x in range(dimx):
            # Get the ID of the current tile
            current_id = grid_map.get((x, y), " ")
            
            # Check the neighbor to the right
            right_id = grid_map.get((x + 1, y), None)
            
            # If we are at the edge OR the neighbor is different, draw a wall
            separator = "|" if (x == dimx - 1 or current_id != right_id) else " "
            
            row_str += f" {current_id} {separator}"
        print(row_str)

        # --- Print Divider Line ---
        # We check the tile BELOW to decide if we need a horizontal line
        div_str = "+"
        for x in range(dimx):
            current_id = grid_map.get((x, y), None)
            below_id   = grid_map.get((x, y + 1), None)
            
            # If we are at the bottom edge OR the neighbor below is different, draw line
            if y == dimy - 1 or current_id != below_id:
                fill = "---"
            else:
                fill = "   "
            div_str += f"{fill}+"
        print(div_str)

tetris_make_tiles()
print_tiles()