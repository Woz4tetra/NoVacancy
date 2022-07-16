
class BaseBoard:
    def __init__(self):
        self.board_id = -1
        self.group = ""
        self.location = ""
        self.type = ""
        self.description = ""
        self.index = -1

    def get_id(self) -> int:
        return self.board_id
    
    def get_description(self) -> str:
        return self.description
    
    def get_location(self) -> str:
        return "%s-%s" % (self.location, self.group)
    
    def get_occupied(self) -> bool:
        return
