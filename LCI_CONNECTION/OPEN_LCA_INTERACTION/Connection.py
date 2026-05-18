import olca_ipc as ipc
import olca_schema as o
client = ipc.Client(8080)  
print("Connected to openLCA IPC server on port 8080")
process_via_id = client.get(o.Process, "dd86962a-dd7e-316b-9ae3-bb22cf1fcbc2")
process_via_name = client.get(o.Process, name="electric connector production, wire clamp | electric connector, wire clamp | APOS, U")

# The following makes sure that both processes are the same:
assert process_via_id.id == process_via_name.id

# Lets print some information:
print("Python Type:", type(process_via_id))
print('ID:', process_via_id.id)
print('Name:', process_via_id.name)