import itarget_connection


class SerialConnectionGeneric(itarget_connection.ITargetConnection):
    """
    ITargetConnection implementation using serial ports. Designed to utilize SerialConnectionLowLevel.

    Since serial ports provide no default functionality for separating messages/packets, this class provides
    several means:
     - timeout: Return received bytes after timeout seconds.
     - msg_separator_time:
                Return received bytes after the wire is silent for a given time.
                This is useful, e.g., for terminal protocols without a machine-readable delimiter.
                A response may take a long time to send its information, and you know the message is done
                when data stops coming.
     - content_check:
                A user-defined function takes the data received so far and checks for a packet.
                The function should return 0 if the packet isn't finished yet, or n if a valid message of n
                bytes has been received. Remaining bytes are stored for next call to recv().

                Example:
                def content_check_newline(data):
                  if data.find('\n') >= 0:
                    return data.find('\n')
                  else:
                    return 0
    If none of these methods are used, your connection may hang forever.
    """

    def __init__(self, connection, timeout=None, message_separator_time=None, content_checker=None):
        """
        @type  connection:             itarget_connection.ITargetConnection
        @param connection:             Low level connection, e.g., SerialConnectionLowLevel.
        @type timeout:                 float
        @param timeout:                For recv(). After timeout seconds from receive start,
                                       recv() will return all received data, if any.
        @type message_separator_time:  float
        @param message_separator_time: After message_separator_time seconds _without receiving any more data_,
                                       recv() will return.
        @type content_checker:         function(str) -> int
        @param content_checker:        (Optional, def=None) User-defined function.
                                           recv() will pass received bytes to this method.
                                           If the method returns n > 0, recv() will return n bytes.
                                           If it returns 0, recv() will keep on reading.
        """
        self._connection = connection
        self._logger = None
        self.timeout = timeout
        self.message_separator_time = message_separator_time
        self.content_checker = content_checker

    def close(self):
        """
        Close connection to the target.

        :return: None
        """
        self._connection.close()

    def open(self):
        """
        Opens connection to the target. Make sure to call close!

        :return: None
        """
        self._connection.open()

    def recv(self, max_bytes):
        """
        Receive up to max_bytes data from the target.

        :param max_bytes: Maximum number of bytes to receive.
        :type max_bytes: int

        :return: Received data.
        """

        self._connection.timeout = min(.001, self.message_separator_time, self.timeout)

        fragment = self._connection.recv(max_bytes=max_bytes)
        data = fragment
        #
        # # Serial ports can be slow and render only a few bytes at a time.
        # # Therefore, we keep reading until we get nothing, in hopes of getting a full packet.
        # while fragment:
        #     # Quit if we find the message terminator
        #     if self.message_terminator is not None and re.search(self.message_terminator, data) is not None:
        #         break
        #     fragment = self._device.read(size=1024)
        #     data += fragment

        return data

    def send(self, data):
        """
        Send data to the target. Only valid after calling open!

        :param data: Data to send.

        :return: None
        """
        bytes_sent = 0
        while bytes_sent < len(data):
            bytes_sent += self._connection.send(data[bytes_sent:])
        return bytes_sent

    def set_logger(self, logger):
        """
        Set this object's (and it's aggregated classes') logger.

        :param logger: Logger to use.
        :type logger: logging.Logger

        :return: None
        """
        self._logger = logger
