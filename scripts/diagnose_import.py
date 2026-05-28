import sys, traceback
sys.path.insert(0, r'C:\Users\alorzaga\Git\tesis\TESIS\annex\LCI')
try:
    import library_sync_cli
    print('imported OK')
except Exception:
    traceback.print_exc()
