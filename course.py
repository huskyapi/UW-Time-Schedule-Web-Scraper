class Course:
    def __init__(self):
        self.name = ""
        self.department = ""
        self.number = ""
        self.section = ""
        self.description = ""
        self.quarter = ""
        self.year = ""
        self.meetings = []
        self.current_size = ""
        self.max_size = ""
        self.lower_credits = ""
        self.upper_credits = ""
        self.add_code_required = False
        self.type = ""
        self.general_education = {
            "C": False,
            "W": False,
            "QSR": False,
            "DIV": False,
            "VLPA": False,
            "IS": False,
            "NW": False
        }
