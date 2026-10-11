/*
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Anderson Nogueira
 * SPI CPOL idle diagnostic. Separate from the validated baseline sketch.
 * ATmega328P / Uno R3, 16 MHz. AVR registers only.
 */
#ifndef F_CPU
#define F_CPU 16000000UL
#endif
#include <avr/io.h>
#include <util/delay.h>
#include <stdint.h>

namespace {
constexpr uint8_t tx_bytes[] = {0xA5, 0x3C, 0x5A};
constexpr uint16_t uart_divisor = 103; // 9600 bps, normal speed
constexpr uint16_t spi_timeout = 60000;

void uart_init() {
  UCSR0A = 0;
  UBRR0H = static_cast<uint8_t>(uart_divisor >> 8);
  UBRR0L = static_cast<uint8_t>(uart_divisor);
  UCSR0B = _BV(TXEN0);
  UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
}
void uart_char(char c) {
  while (!(UCSR0A & _BV(UDRE0))) {}
  UDR0 = static_cast<uint8_t>(c);
}
void uart_text(const char* s) {
  while (*s) uart_char(*s++);
}
void uart_hex(uint8_t data) {
  const char hexdigits[] = "0123456789ABCDEF";
  uart_char(hexdigits[(data >> 4) & 0x0F]);
  uart_char(hexdigits[data & 0x0F]);
}
void uart_digit(uint8_t data) {
  uart_char(static_cast<char>('0' + data));
}

void pins_init() {
  // SS=PB2 (D10), MOSI=PB3 (D11), SCK=PB5 (D13).
  PORTB |= _BV(PORTB2); // SS HIGH before SPI master enabled.
  DDRB |= _BV(DDB0) | _BV(DDB1) | _BV(DDB2) | _BV(DDB3) | _BV(DDB5);
  DDRB &= static_cast<uint8_t>(~_BV(DDB4)); // MISO=PB4 (D12) input.
  PORTB &= static_cast<uint8_t>(~_BV(PORTB4));
  DDRD |= _BV(DDD7); // D7 = idle-window marker.
  PORTD &= static_cast<uint8_t>(~_BV(PORTD7));
  SPSR &= static_cast<uint8_t>(~_BV(SPI2X));
  SPCR = _BV(SPE) | _BV(MSTR) | _BV(SPR0); // Master, fCPU/16.
}

void select_mode(uint8_t mode) {
  // D8, D9 encode selected mode as two binary bits.
  PORTB = static_cast<uint8_t>((PORTB & ~(_BV(PORTB0) | _BV(PORTB1)))
      | ((mode & 1) ? _BV(PORTB0) : 0)
      | ((mode & 2) ? _BV(PORTB1) : 0));
  uint8_t control = _BV(SPE) | _BV(MSTR) | _BV(SPR0);
  if (mode & 2) control |= _BV(CPOL);
  if (mode & 1) control |= _BV(CPHA);
  SPCR = control;
}

bool exchange(uint8_t tx, uint8_t& rx) {
  SPDR = tx;
  for (uint16_t i = 0; i < spi_timeout; ++i) {
    if (SPSR & _BV(SPIF)) {
      rx = SPDR;
      return true;
    }
  }
  return false;
}

void probe_mode(uint8_t mode) {
  PORTB |= _BV(PORTB2); // Idle always has SS HIGH.
  select_mode(mode);
  uart_text("CPOL PROBE mode="); uart_digit(mode);
  uart_text(" CPOL="); uart_digit(static_cast<uint8_t>((mode >> 1) & 1));
  uart_text(" CPHA="); uart_digit(static_cast<uint8_t>(mode & 1));
  uart_text("\r\n");

  PORTD |= _BV(PORTD7); // PRE window: explicit high marker, no SPI clock.
  _delay_ms(700);
  PORTD &= static_cast<uint8_t>(~_BV(PORTD7));
  _delay_us(30);

  uint8_t received[3] = {0, 0, 0};
  bool good[3] = {false, false, false};
  PORTB &= static_cast<uint8_t>(~_BV(PORTB2)); // SS LOW.
  _delay_us(20);
  for (uint8_t i = 0; i < 3; ++i) {
    good[i] = exchange(tx_bytes[i], received[i]);
  }
  _delay_us(20);
  PORTB |= _BV(PORTB2); // SS HIGH before UART output.

  PORTD |= _BV(PORTD7); // POST window: SCK should return to CPOL idle.
  _delay_ms(350);
  PORTD &= static_cast<uint8_t>(~_BV(PORTD7));

  for (uint8_t i = 0; i < 3; ++i) {
    uart_text("TX="); uart_hex(tx_bytes[i]);
    uart_text(" RX="); uart_hex(received[i]);
    uart_text(good[i] && (received[i] == tx_bytes[i])
      ? " LOOPBACK_PASS\r\n" : " FAIL_OR_TIMEOUT\r\n");
  }
  _delay_ms(120);
}
} // namespace

void setup() {
  uart_init();
  pins_init();
  uart_text("SHINOBI AVR SPI CPOL idle-window probe; D8/D9=mode, D7=idle\r\n");
}
void loop() {
  for (uint8_t mode = 0; mode < 4; ++mode) {
    probe_mode(mode);
  }
  _delay_ms(500);
}
