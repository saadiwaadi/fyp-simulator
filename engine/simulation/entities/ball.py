class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.z = 0

        self.vx = 0
        self.vy = 0
        self.vz = 0

        self.owner = None

    def position(self):
        return (self.x, self.y, self.z)

    def predict_position(self, ticks=3, friction=0.9):
        vx = self.vx
        vy = self.vy
        x = self.x
        y = self.y

        for _ in range(ticks):
            x += vx
            y += vy
            vx *= friction
            vy *= friction

        return (x, y)

    def attach_to_owner(self, owner, x=None, y=None):
        self.owner = owner
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        self.z = 0
        self.vx = 0
        self.vy = 0
        self.vz = 0

    def release(self):
        self.owner = None

    def update(self):
        if self.owner is not None:
            owner_x = getattr(self.owner, 'x', None)
            owner_y = getattr(self.owner, 'y', None)
            if owner_x is not None and owner_y is not None:
                self.x = owner_x
                self.y = owner_y
                self.z = 0
            return

        self.x += self.vx
        self.y += self.vy
        self.z += self.vz

        self.vz -= 0.2

        if self.z < 0:
            self.z = 0
            self.vz *= -0.3
