/*
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Anderson Nogueira
 * SHINOBI AVR SPI register readback + SCK GPIO control probe.
 *
 * Diagnostic ONLY: leaves the baseline firmware untouched.
 * ATmega328P @ 16 MHz, SPI fSCK = 1 MHz (F_CPU/16).
 * No Arduino GPIO, SPI, Serial or delay API.
 */
#ifndef F_CPU
#define F_CPU 16000000UL
#endif
#include <avr/io.h>
#include <util/delay.h>
#include <stdint.h>

namespace {
constexpr uint16_t kUartDiv = 103;  // 9600 bps @ 16MHz, normal speed.
constexpr uint16_t kPollLimit = 60000;
constexpr uint8_t kTx[3] = {0xA5, 0x3C, 0x5A};

void tx_char(char c) {
  while (!(UCSR0A & _BV(UDRE0))) {}
  UDR0 = static_cast<uint8_t>(c);
}
void tx_text(const char* s) {
  while (*s) tx_char(*s++);
}
void tx_hex(uint8_t v) {
  const char h[] = "0123456789ABCDEF";
  tx_char(h[(v >> 4) & 0x0F]);
  tx_char(h[v & 0x0F]);
}
void tx_bit(bool v) {
  tx_char(v ? '1' : '0');
}
void tx_mode(uint8_t m) {
  tx_char(static_cast<char>('0' + m));
}
void uart_init() {
  UCSR0A = 0;
  UBRR0H = static_cast<uint8_t>(kUartDiv >> 8);
  UBRR0L = static_cast<uint8_t>(kUartDiv);
  UCSR0B = _BV(TXEN0);
  UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
}

void init_gpio() {
  // PB0/D8=MODE_LSB, PB1/D9=MODE_MSB, PB2/D10=SS
  // PB3/D11=MOSI, PB4/D12=MISO input, PB5/D13=SCK.
  PORTB |= _BV(PORTB2); // Hold hardware SS HIGH.
  DDRB |= _BV(DDB0) | _BV(DDB1) | _BV(DDB2) | _BV(DDB3) | _BV(DDB5);
  DDRB &= static_cast<uint8_t>(~_BV(DDB4));
  PORTB &= static_cast<uint8_t>(~_BV(PORTB4));
  // PD7/D7=WINDOW, PD6/D6=SPI_ENABLED marker.
  DDRD |= _BV(DDD6) | _BV(DDD7);
  PORTD &= static_cast<uint8_t>(~(_BV(PORTD6) | _BV(PORTD7)));
  SPCR = 0;
  SPSR &= static_cast<uint8_t>(~_BV(SPI2X));
}

bool sck_pin_high() {
  return (PINB & _BV(PINB5)) != 0;
}
void mark_window(bool on) {
  if (on) PORTD |= _BV(PORTD7);
  else PORTD &= static_cast<uint8_t>(~_BV(PORTD7));
}
void mark_spi(bool on) {
  if (on) PORTD |= _BV(PORTD6);
  else PORTD &= static_cast<uint8_t>(~_BV(PORTD6));
}
void mode_markers(uint8_t mode) {
  uint8_t bits = 0;
  if (mode & 1) bits |= _BV(PORTB0);
  if (mode & 2) bits |= _BV(PORTB1);
  PORTB = static_cast<uint8_t>((PORTB & ~(_BV(PORTB0) | _BV(PORTB1))) | bits);
}
uint8_t spi_config(uint8_t mode) {
  uint8_t ctrl = _BV(SPE) | _BV(MSTR) | _BV(SPR0); // F_CPU/16.
  if (mode & 2) ctrl |= _BV(CPOL);
  if (mode & 1) ctrl |= _BV(CPHA);
  return ctrl;
}
bool exchange(uint8_t tx, uint8_t& rx) {
  SPDR = tx;
  for (uint16_t i = 0; i < kPollLimit; ++i) {
    if (SPSR & _BV(SPIF)) {
      rx = SPDR;
      return true;
    }
  }
  return false;
}

void probe_mode(uint8_t mode) {
  PORTB |= _BV(PORTB2); // SS remains HIGH while measuring idle SCK.
  mode_markers(mode);

  // CONTROL: SPI disabled. Confirm the analyzer sees GPIO-controlled SCK HIGH.
  SPCR = 0;
  mark_spi(false);
  PORTB |= _BV(PORTB5);
  mark_window(true);        // D7 HIGH, D6 LOW = GPIO control.
  _delay_ms(250);
  const bool gpio_high = sck_pin_high();
  mark_window(false);

  // Release the positive control, return GPIO SCK LOW BEFORE SPI enables.
  PORTB &= static_cast<uint8_t>(~_BV(PORTB5));
  _delay_ms(40);

  // SPI control: independent SPCR readback and physical pin sample.
  const uint8_t requested = spi_config(mode);
  SPCR = requested;
  mark_spi(true);           // D6 HIGH = SPI enabled, D7 low outside window.
  _delay_ms(40);
  mark_window(true);        // D7 HIGH, D6 HIGH = SPI idle pre-window.
  _delay_ms(400);
  const uint8_t spcr_readback = SPCR;
  const bool spi_idle_pre = sck_pin_high();
  mark_window(false);

  // Group three SPI bytes under a single short SS LOW transaction.
  _delay_us(30);
  uint8_t rx[3] = {0, 0, 0};
  bool pass[3] = {false, false, false};
  PORTB &= static_cast<uint8_t>(~_BV(PORTB2)); // Assert SS.
  _delay_us(20);
  for (uint8_t i = 0; i < 3; ++i) {
    pass[i] = exchange(kTx[i], rx[i]);
  }
  _delay_us(20);
  PORTB |= _BV(PORTB2); // Release SS.

  // Observe SCK after data is complete, while SPI remains enabled.
  mark_window(true);
  _delay_ms(250);
  const bool spi_idle_post = sck_pin_high();
  mark_window(false);

  // Disable peripheral after the post-window. GPIO latch stays LOW.
  SPCR = 0;
  mark_spi(false);
  _delay_ms(20);

  // Print only after SS HIGH and outside all measurement windows.
  tx_text("MODE="); tx_mode(mode);
  tx_text(" REQUESTED_SPCR=0x"); tx_hex(requested);
  tx_text(" READBACK_SPCR=0x"); tx_hex(spcr_readback);
  tx_text(" READBACK_CPOL="); tx_bit((spcr_readback & _BV(CPOL)) != 0);
  tx_text(" READBACK_CPHA="); tx_bit((spcr_readback & _BV(CPHA)) != 0);
  tx_text(" GPIO_SCK="); tx_bit(gpio_high);
  tx_text(" SPI_IDLE_PRE="); tx_bit(spi_idle_pre);
  tx_text(" SPI_IDLE_POST="); tx_bit(spi_idle_post);
  tx_text("\r\n");
  for (uint8_t i = 0; i < 3; ++i) {
    tx_text("TX=0x"); tx_hex(kTx[i]);
    tx_text(" RX=0x"); tx_hex(rx[i]);
    tx_text(pass[i] && rx[i] == kTx[i] ? " LOOPBACK_PASS\r\n" : " FAIL_OR_TIMEOUT\r\n");
  }
  _delay_ms(120);
}
} // namespace

void setup() {
  uart_init();
  init_gpio();
  tx_text("SHINOBI SPI: GPIO SCK control vs SPCR CPOL/CPHA readback\r\n");
}
void loop() {
  for (uint8_t mode = 0; mode < 4; ++mode) {
    probe_mode(mode);
  }
  _delay_ms(400);
}
