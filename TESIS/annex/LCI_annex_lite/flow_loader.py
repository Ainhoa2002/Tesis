import csv
import re
import logging
try:
    from .parameter_library import list_params
except Exception as exc:
    logging.warning("parameter_library.list_params not available: %s", exc)
    def list_params():
        return {}

def eval_expr(expr, params):
    expr = re.sub(r'\$\{(\w+)\}', lambda m: str(params.get(m.group(1), m.group(0))), expr)
    try:
        return eval(expr)
    except Exception as exc:
        logging.debug("Could not evaluate expression '%s': %s", expr, exc)
        return expr

def load_flows_with_parameters(csv_path):
    params = list_params()
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        flows = []
        for row in reader:
            amount = row['Amount']
            if isinstance(amount, str) and '${' in amount:
                row['Amount'] = str(eval_expr(amount, params))
            flows.append(row)
    return flows