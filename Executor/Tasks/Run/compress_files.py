from Task import Task
from Helper import Level
from os.path import abspath


class CompressFiles(Task):
    def __init__(self, logMethod, parent, params):
        super().__init__("Compress Files", parent, params, logMethod, None)
        self.paramRules = {
            'Files': ([], False),
            'Folders': ([], False),
            'Output': (None, True)
        }

    def Run(self):
        from Helper import Compress, IO

        files = [
            abspath(f["Source"] if isinstance(f, dict) else f)
            for f in self.params["Files"]
        ]

        folders = [
            abspath(folder)
            for folder in self.params["Folders"]
        ]

        output = self.params["Output"]

        self.Log(Level.INFO, f"Compressing files to output: {output}")

        for folder in folders:
            files.extend(IO.GetAllFiles(folder))

        self.Log(Level.DEBUG, f"Files to compress: {files}")

        try:
            Compress.Zip(files, output)
            self.Log(Level.INFO, "File created")
            self.parent.GeneratedFiles.append(output)

        except Exception as e:
            self.SetVerdictOnError()
            self.Log(
                Level.ERROR,
                f"Exception while creating zip file: {e}"
            )
