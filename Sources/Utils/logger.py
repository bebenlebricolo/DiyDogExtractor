from pathlib import Path

class Logger :
    filepath : Path
    _first_run : bool = True


    def __init__(self, filepath : Path) -> None:
        self.filepath = filepath

    def log(self, msg : str) :
        # Create directory if need be
        if self._first_run :
            if not self.filepath.parent.exists() :
                self.filepath.parent.mkdir(parents=True)
            else :
                # Flush file
                with open(self.filepath, "w") as file :
                    file.write("")
            self._first_run = False

        with open(self.filepath, "a") as file :
            file.write(msg + "\n")
        print(msg)
