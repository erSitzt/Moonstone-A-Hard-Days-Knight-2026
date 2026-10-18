/* Musashi configuration for the macOS/Linux build (selected via MUSASHI_CNF).
 * Mirrors the engine's requirements without editing vendor/Musashi-master:
 *   - moon_instr_hook runs before every instruction (PC hooks, disk swaps, fixes)
 *   - moon_illegal_hook lets Mog's movec CPU probe vector through $10
 *   - 68000 TRACE emulation for Mog's single-stepping decryptor (RE_NOTES.md)
 *   - moon_trap_hook logs TRAP #n and lets the normal exception proceed
 * Every other option keeps Musashi's default from m68kconf.h. */
#ifndef MOON_M68KCONF_H
#define MOON_M68KCONF_H

void moon_instr_hook(unsigned int pc);
int moon_illegal_hook(int opcode);
int moon_trap_hook(int trap);

#define M68K_INSTRUCTION_HOOK       M68K_OPT_SPECIFY_HANDLER
#define M68K_INSTRUCTION_CALLBACK(pc) moon_instr_hook(pc)
#define M68K_ILLG_HAS_CALLBACK      M68K_OPT_SPECIFY_HANDLER
#define M68K_ILLG_CALLBACK(opcode)  moon_illegal_hook(opcode)
#define M68K_TRAP_HAS_CALLBACK      M68K_OPT_SPECIFY_HANDLER
#define M68K_TRAP_CALLBACK(trap)    moon_trap_hook(trap)
#define M68K_EMULATE_TRACE          M68K_OPT_ON

#include "m68kconf.h"

#endif
