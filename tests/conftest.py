import datar
from dotenv import load_dotenv

datar.options(backends=["numpy", "pandas"])
load_dotenv()
