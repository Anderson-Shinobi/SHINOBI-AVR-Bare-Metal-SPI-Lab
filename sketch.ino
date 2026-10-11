/*
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Anderson Nogueira
 * SHINOBI AVR Bare-Metal SPI Lab — ATmega328P @ 16 MHz.
 * Register-level SPI master, UART diagnostics; no Arduino peripheral API.
 * Wokwi sketch uses only the Arduino startup wrapper (setup/loop).
 */
#ifndef F_CPU
#define F_CPU 16000000UL
#endif
#include <avr/io.h>
#include <util/delay.h>
#include <stdint.h>

namespace {
constexpr uint16_t kUartUBRR = 103;  // 9600 baud, 8N1, U2X0=0
constexpr uint16_t kSpiPollLimit = 60000;
const uint8_t kTxPattern[3] = {0xA5, 0x3C, 0x5A};

void uart_init() {
  UCSR0A = 0;
  UBRR0H = static_cast<uint8_t>(kUartUBRR >> 8);
  UBRR0L = static_cast<uint8_t>(kUartUBRR);
  UCSR0B = _BV(TXEN0);
  UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
}
void uart_char(char c) {
  while (!(UCSR0A & _BV(UDRE0))) {}
  UDR0 = static_cast<uint8_t>(c);
}
void uart_text(const char* s) { while (*s) uart_char(*s++); }
void uart_hex(uint8_t v) {
  const char digits[] = "0123456789ABCDEF";
  uart_char(digits[(v >> 4) & 0x0F]);
  uart_char(digits[v & 0x0F]);
}
void uart_decimal(uint8_t v) { uart_char(static_cast<char>('0' + v)); }

void spi_master_init() {
  PORTB |= _BV(PORTB2);
  DDRB |= _BV(DDB2) | _BV(DDB3) | _BV(DDB5);
  DDRB &= static_cast<uint8_t>(~_BV(DDB4));
  PORTB &= static_cast<uint8_t>(~_BV(PORTB4));
  SPCR = _BV(SPE) | _BV(MSTR) | _BV(SPR0);
  SPSR &= static_cast<uint8_t>(~_BV(SPI2X));
}
void spi_set_mode(uint8_t mode) {
  uint8_t ctrl = _BV(SPE) | _BV(MSTR) | _BV(SPR0);
  if (mode & 2) ctrl |= _BV(CPOL);
  if (mode & 1) ctrl |= _BV(CPHA);
  SPCR = ctrl;
}
bool spi_exchange(uint8_t tx, uint8_t& rx) {
  SPDR = tx;
  for (uint16_t wait = 0; wait < kSpiPollLimit; ++wait) {
    if (SPSR & _BV(SPIF)) {
      rx = SPDR;
      return true;
    }
  }
  return false;
}
void transact_mode(uint8_t mode) {
  PORTB |= _BV(PORTB2);
  spi_set_mode(mode);
  uart_text("SPI mode "); uart_decimal(mode); uart_text("; fSCK=1000000 Hz\r\n");
  PORTB &= static_cast<uint8_t>(~_BV(PORTB2));
  for (uint8_t i = 0; i < 3; ++i) {
    uint8_t rx = 0;
    bool ok = spi_exchange(kTxPattern[i], rx);
    uart_text("TX=0x"); uart_hex(kTxPattern[i]);
    if (ok) {
      uart_text(" RX=0x"); uart_hex(rx);
      uart_text(rx == kTxPattern[i] ? " LOOPBACK_PASS\r\n" : " LOOPBACK_MISMATCH\r\n");
    } else { uart_text(" TIMEOUT\r\n"); }
  }
  PORTB |= _BV(PORTB2);
}
}

void setup() {
  uart_init();
  spi_master_init();
  uart_text("SHINOBI AVR SPI register-level loopback (D11->D12)\r\n");
}
void loop() {
  for (uint8_t mode = 0; mode < 4; ++mode) {
    transact_mode(mode);
    _delay_ms(800);
  }
  _delay_ms(1000);
}
