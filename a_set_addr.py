from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse


class ModbusClientWrapper:
    def __init__(self, port, baudrate=9600, parity='N', stopbits=1, bytesize=8, timeout=1):
        # Инициализация Modbus-клиента
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout
        )
        # Подключение к устройству
        self.client.connect()
        self.last_command = None  # Для хранения последней отправленной команды

    def __del__(self):
        # Закрытие соединения при удалении объекта
        if hasattr(self, 'client') and self.client:
            self.client.close()

    def send_command(self, command, *args, **kwargs):
        """Отправка команды с проверкой на эхо."""
        # Сохраняем последнюю команду
        self.last_command = (command, args, kwargs)

        # Отправляем команду
        response = command(*args, **kwargs)

        # Проверяем, не является ли ответ эхом (дублированием последней команды)
        if self.is_echo(response):
            print("Обнаружено эхо. Игнорируем ответ.")
            return None

        return response

    def is_echo(self, response):
        """Проверка, является ли ответ эхом последней команды."""
        if self.last_command is None:
            return False

        # Пример логики для проверки эха:
        # Если ответ содержит те же данные, что и последняя команда, это эхо
        command, args, kwargs = self.last_command
        if isinstance(response, (ModbusIOException, ExceptionResponse)):
            return False  # Ошибки не считаем эхом

        # Пример: сравниваем данные ответа с данными команды
        if hasattr(response, 'registers'):
            # Для чтения регистров
            return response.registers == kwargs.get('value', args[1] if len(args) > 1 else None)
        elif hasattr(response, 'value'):
            # Для записи регистров
            return response.value == kwargs.get('value', args[1] if len(args) > 1 else None)

        return False

    def find_devices(self):
        """Поиск всех устройств на шине Modbus."""
        devices = []
        for slave_id in range(1, 20):  # Адреса устройств от 1 до 247
            try:
                # Попытка чтения holding регистра для проверки наличия устройства
                response = self.send_command(
                    self.client.read_holding_registers,
                    address=0,
                    count=1,
                    slave=slave_id
                )
                if response is None:  # Пропустить эхо
                    continue
                if not isinstance(response, (ModbusIOException, ExceptionResponse)):
                    devices.append(slave_id)
            except Exception as e:
                print(f"Ошибка при поиске устройства {slave_id}: {e}")
        return devices

    def change_device_id(self, current_id, new_id):
        """Изменение ID устройства."""
        # Предполагаем, что команда для изменения ID устройства записывается в регистр 0x0110
        response = self.send_command(
            self.client.write_register,
            address=0x0110,
            value=new_id,
            slave=current_id
        )
        if response is None:  # Пропустить эхо
            return False
        if isinstance(response, (ModbusIOException, ExceptionResponse)):
            print(f"Modbus IO Error: {response}")
            return False
        return True


# Основной код программы
if __name__ == "__main__":
    # Инициализация Modbus-клиента
    modbus_client = ModbusClientWrapper(port='COM10', baudrate=9600)  # Укажите правильный порт

    # Поиск устройств на шине
    print("Поиск устройств...")
    devices = modbus_client.find_devices()

    if devices:
        print(f"Найдено {len(devices)} устройств с адресами: {', '.join(map(str, devices))}")

        # Предложение изменить адрес одного из устройств
        try:
            current_address = int(input("Введите текущий адрес устройства, которое хотите изменить: "))
            if current_address not in devices:
                print("Устройство с таким адресом не найдено.")
            else:
                new_address = int(input("Введите новый адрес (1-247): "))
                if 1 <= new_address <= 247:
                    success = modbus_client.change_device_id(current_address, new_address)
                    if success:
                        print(f"Адрес {current_address} успешно изменён на {new_address}.")
                    else:
                        print("Не удалось изменить адрес устройства.")
                else:
                    print("Новый адрес должен быть в диапазоне от 1 до 247.")
        except ValueError:
            print("Ошибка ввода. Пожалуйста, введите число.")
    else:
        print("Не найдено ни одного устройства.")