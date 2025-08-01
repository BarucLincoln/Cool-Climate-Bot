#!/bin/sh

# Este é um script de shell que executa nosso bot.
# O comando 'exec' é crucial: ele substitui o processo do shell
# pelo processo do Python. Isso faz com que o bot seja o processo
# principal da máquina, impedindo que ela desligue.

exec python main.py
