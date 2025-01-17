import requests
from dotenv import load_dotenv
import os
import json
import pandas as pd
import re
from copy import deepcopy

# {"object":"error","status":400,"code":"validation_error","message":"body failed validation: body.children[1].toggle.rich_text[1].equation.expression should be    
# populated, instead was `\"\"`.","request_id":"49314dd8-1bb3-4f53-9b9a-b9c27e1b77b0"}の場合に対処するためのテスト