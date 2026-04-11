import math


class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.danger = 0
        self.occupied = False
        self.occupant = None


class Field:
    def __init__(self, config):
        pitch_size = config.get('pitch_size', (20, 13)) if config else (20, 13)
        self.width, self.height = pitch_size
        self.zone_names = ('Left', 'Center', 'Right')
        self.nodes = self._create_grid()

    def _create_grid(self):
        grid = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                row.append(Node(x, y))
            grid.append(row)
        return grid

    def get_node(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.nodes[y][x]
        return None

    def get_neighbors(self, x, y):
        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1),
        ]

        neighbors = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                neighbors.append((nx, ny))
        return neighbors

    def distance(self, a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def clamp_position(self, x, y):
        x = max(0, min(x, self.width - 1))
        y = max(0, min(y, self.height - 1))
        return x, y

    def is_in_final_third(self, position):
        return position[0] > self.width * 0.66

    def is_wide_area(self, position):
        return position[1] < 3 or position[1] > self.height - 3

    def is_central(self, position):
        return 3 <= position[1] <= self.height - 3

    def zone_for_position(self, position):
        x, _ = position
        left_cut = self.width / 3.0
        right_cut = (self.width * 2.0) / 3.0

        if x < left_cut:
            return 'Left'
        if x < right_cut:
            return 'Center'
        return 'Right'

    def iter_nodes(self):
        for row in self.nodes:
            for node in row:
                yield node
