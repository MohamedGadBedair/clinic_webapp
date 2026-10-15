import enum

# =========================={Enums}============================
class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"

class UserRole(enum.Enum):
    CLIENT = "client"
    # ASSESTANT = "assestant"
    DOCTOR = "doctor"
    # ADMIN = "admin"

class AppointmentStatus(enum.Enum):
    CONFIRMED = "confirmed"
    WAITING = "waiting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

class MedicalFileType(enum.Enum):
    LAB = "lab"
    IMAGING = "imaging"
    REPORT = "report"

class City(enum.Enum):
  None
  CAIRO = "Cairo"
  ALEXANDRIA = "Alexandria"
  GIZA = "Giza"
  SHUBRA_EL_KHEIMA = "Shubra El Kheima"
  PORT_SAID = "Port Said"
  SUEZ = "Suez"
  LUXOR = "Luxor"
  MANSOURA = "Mansoura"
  EL_MAHALLA_EL_KUBRA = "El Mahalla El Kubra"
  TANTA = "Tanta"
  ASYUT = "Asyut"
  ISMAILIA = "Ismailia"
  FAIYUM = "Faiyum"
  ZAGAZIG = "Zagazig"
  ASWAN = "Aswan"
  DAMIETTA = "Damietta"
  DAMANHUR = "Damanhur"
  MINYA = "Minya"
  BENI_SUEF = "Beni Suef"
  HURGHADA = "Hurghada"
  QENA = "Qena"
  SOHAG = "Sohag"
  SHARM_EL_SHEIKH = "Sharm El Sheikh"
  BANHA = "Banha"
  # وممكن تضيف أي مدينة تانية محتاجها...
