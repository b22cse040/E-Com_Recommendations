import logging
import sys


def configure_logging() -> logging.Logger:
  """
  Configures and returns a global logger instance.
  Logs to both console and a file named 'walmart.log'.
  """
  logger_obj = logging.getLogger("walmart_rag")
  logger_obj.setLevel(logging.INFO)  # Set the desired global logging level

  # Prevent adding handlers multiple times if this function is called repeatedly
  if logger_obj.hasHandlers():
    return logger_obj

  # Create handlers
  console_handler = logging.StreamHandler(sys.stdout)
  file_handler = logging.FileHandler("walmant.log")

  # Create formatter and set it for both handlers
  formatter = logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s [%(filename)s:%(lineno)d] - %(message)s'
  )
  console_handler.setFormatter(formatter)
  file_handler.setFormatter(formatter)

  # Add handlers to the logger
  logger_obj.addHandler(console_handler)
  logger_obj.addHandler(file_handler)

  return logger_obj


# Create a logger instance to be imported by other modules
logger: logging.Logger = configure_logging()
