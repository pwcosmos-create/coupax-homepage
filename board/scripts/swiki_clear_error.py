import agent_office_swiki_sync as s

st = s.load_state()
st["last_error"] = ""
s.save_state(st)
print("ok")
