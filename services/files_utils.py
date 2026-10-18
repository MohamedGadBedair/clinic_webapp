import uuid
from pathlib import Path


CLIENTS_FILES_DIR = Path("uploads")

# process client file func
def process_client_files(content:bytes,extension:str)->str:
        # rename the file
        filename=f'{uuid.uuid4().hex}.{extension}'
        filepath=CLIENTS_FILES_DIR/filename
        # content=BytesIO(content)
        CLIENTS_FILES_DIR.mkdir(parents=True,exist_ok=True)
        # check if the file already exists
        if filepath.exists():
            filename=f'{uuid.uuid4().hex}.{extension}'
            filepath=CLIENTS_FILES_DIR/filename
        # save the file
        with open(filepath,'wb') as f:
            f.write(content)

        return filename
    
# delete client file func
def delete_client_file(filename:str|None)->None:
    if not filename:
        return
    
    filepath= CLIENTS_FILES_DIR/filename
    if filepath.exists():
        filepath.unlink()