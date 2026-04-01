import olca_ipc as ipc
import olca_schema as o

def find_flows_by_name(client, search_term):
    """Search for flows whose names contain the search term."""
    print(f"\nSearching for flows containing '{search_term}':")
    # Get all flow descriptors (this may take a moment for large databases)
    descriptors = client.get_descriptors(o.Flow)
    # Filter those whose name contains the search term (case-insensitive)
    matches = [d for d in descriptors if search_term.lower() in d.name.lower()]
    if not matches:
        print("  No flows found.")
        return
    print(f"  Found {len(matches)} flow(s):")
    for d in matches[:10]:  # show up to 10
        # Get full flow object to ensure we have the UUID
        flow = client.get(o.Flow, uid=d.id)
        if flow:
            print(f"    Name: {flow.name}")
            print(f"    UUID: {flow.id}\n")

def main():
    client = ipc.Client(8080)   # or ipc.IpC(8080)
    print("Connected to openLCA")
    search_term = input("Enter a search term: ").strip()
    if search_term:
        find_flows_by_name(client, search_term)
    else:
        print("No search term entered.")

if __name__ == "__main__":
    main()