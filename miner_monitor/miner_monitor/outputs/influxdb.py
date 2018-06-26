#!/usr/bin/env python3

import time
from typing import *

from .__init__ import IOutput


class InfluxDB(IOutput):
    def __init__(self, connection: Dict, config: Dict):
        super().__init__(connection, config)

    @classmethod
    def _remove_unit(cls, s: str) -> float:
        num, unit = s.split()
        num = float(num)
        unit = unit.lower()
        if unit.startswith("k"):
            num *= 1000
        elif unit.startswith("m"):
            num *= 1000000
        return num

    @staticmethod
    def _time_format(t: int) -> int:
        """
        Converts a integer timestamp to InfluxDB format.
        :param t: timestamp format which you can get with int(time.time()).
        :return: InfluxDB acceptable timestamp value.
        """
        return t * 1000000000

    @staticmethod
    def _any_format(a: any) -> str:
        """
        Converts dict value to InfluxDB line protocol acceptable format.

        Formats according to document:
            Float IEEE754
            Integer 64-bit signed with a trailing 'i'
            String <=64KiB
            Boolean [t, T, true, True, TRUE]; [f, F, false, False, FALSE]

        :param a: any value that is supported.
        :return: a string that can directly be embedded into line protocol.
        """
        ret = ""

        if isinstance(a, time):
            ret = str(InfluxDB._time_format(a))
        elif isinstance(a, bool):
            ret = "T" if a else "F"
        elif isinstance(a, float):
            # TODO: need review on IEEE754 string representation
            ret = str(a)
        elif isinstance(a, int):
            ret = str(a) + "i"
        else:
            try:
                ret = '"' + str(a).replace("\"", "\\\"") + '"'
            except:
                raise NotImplemented("Doesn't know how to convert class {} to string".format(type(a).__name__))

        return ret

    @staticmethod
    def _name_escape(s: str) -> str:
        """
        Apple this escape rule for tag keys, tag values, and field keys.
        :param s:
        :return:
        """
        return s.replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")

    @staticmethod
    def _measurement_escape(s: str) -> str:
        """
        Apply this escape rule for measurements.
        :param s:
        :return:
        """
        return s.replace(",", "\\,").replace(" ", "\\ ")

    @staticmethod
    def _dict_format(d: Dict[str, any], key_converter: function = None, value_converter: function = None) -> str:
        """
        Convert dict to InfluxDB line protocol "key1=value1[,key2=value2[,...]]" format.
        :param d: dict containing all (k, v) pairs
        :return: a string
        """

        def _null_converter(s: str) -> str:
            return s

        if key_converter is None:
            key_converter = _null_converter
        if value_converter is None:
            value_converter = _null_converter
        return ",".join("{}={}".format(key_converter(k), value_converter(InfluxDB._any_format(v))) for k, v in d)

    @staticmethod
    def _line_protocol(self, measurement: str, tags: Dict[str, any], data: Dict[str, any],
                       timestamp: Union[int, time]) -> str:
        """
        Generate line protocol line.
        :param measurement:
        :param tags:
        :param data:
        :param timestamp: Timestamp in nanosecond, 64-bit signed integer or T-Z format (1677-09-21T00:12:43.145224194Z)
        :return: InfluxDB line protocol line without trailing \n
        """
        return "{},{} {} {}".format(self._measurement_escape(measurement),
                                    self._dict_format(
                                        tags.items(),
                                        key_converter=self._name_escape,
                                        value_converter=self._name_escape,
                                    ),
                                    self._dict_format(
                                        data.items(),
                                        key_converter=self._name_escape,
                                    ),
                                    str(self._time_format(
                                        int(timestamp) if isinstance(timestamp, time) else timestamp)))
