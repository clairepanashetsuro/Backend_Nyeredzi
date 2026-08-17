# Auto-register all models to Base.metadata
try:
    from .user import User
    from .location import Location
    from .farmer import Farmer
    from .extension_worker import ExtensionWorker
    from .farmer_request import FarmerRequest
    from .field_image import FieldImage
    from .field_report import FieldReport
    from .ussd import USSDSession
except ImportError as e:
    print(f"Model registration warning: {e}")
