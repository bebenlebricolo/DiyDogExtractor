import sys
from pathlib import Path

class Logger :
    filepath : Path
    _first_run : bool = True


    def __init__(self, filepath : Path) -> None:
        self.filepath = filepath

    def log(self, msg : str) :
        # Create directory if need be
        print_msg = (msg + "\n")
        if self._first_run :
            if not self.filepath.parent.exists() :
                self.filepath.parent.mkdir(parents=True)
            else :
                # Flush file
                with open(self.filepath, "w", encoding="utf-8") as file :
                    file.write("")
            self._first_run = False

        with open(self.filepath, "a", encoding="utf-8") as file :
            file.write(print_msg)
        #print(msg)
        sys.stdout.buffer.write(print_msg.encode("utf-8"))
