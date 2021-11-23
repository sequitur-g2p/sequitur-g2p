/*
 * $Id: Assertions.cc 1667 2007-06-02 14:32:35Z max $
 *
 * Copyright (c) 2004-2005  RWTH Aachen University
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License Version 2 (June
 * 1991) as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, you will find it at
 * http://www.gnu.org/licenses/gpl.html, or write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110,
 * USA.
 *
 * Should a provision of no. 9 and 10 of the GNU General Public License
 * be invalid or become invalid, a valid provision is deemed to have been
 * agreed upon which comes closest to what the parties intended
 * commercially. In any case guarantee/warranty shall be limited to gross
 * negligent actions or intended actions or fraudulent concealment.
 */

#include "Assertions.hh"

#include <errno.h>
#ifdef _HAS_TRACEBACK_
#include <execinfo.h>
#endif
#include <signal.h>
#include <cstring>
#include <cstdlib>
#include <sstream>
#include <stdexcept>


namespace AssertionsPrivate {

void stackTrace(std::ostream &os, int cutoff) {
#ifdef _HAS_TRACEBACK_
    os << "stack trace (innermost first):" << std::endl;
    static const size_t maxTraces = 100;
    void *array[maxTraces];
    size_t nTraces = backtrace(array, maxTraces);
    char **strings = backtrace_symbols(array, nTraces);
    for (size_t i = cutoff+1; i < nTraces; i++)
        os << '#' << i << "  " << strings[i] << std::endl;
    free(strings);
#endif
}

void assertionFailed(const char *type,
                     const char *expr,
                     const char *function,
                     const char *filename,
                     unsigned int line) {
    std::ostringstream msg;
    msg << std::endl << std::endl
        << "PROGRAM DEFECTIVE:"
        << std::endl
        << type << ' ' << expr << " violated" << std::endl
        << "in " << function
        << " file " << filename << " line " << line << std::endl
        << std::endl;
    stackTrace(msg, 1);
    msg << std::endl;
    throw std::logic_error(msg.str());
}

void hopeDisappointed(const char *expr,
                      const char *function,
                      const char *filename,
                      unsigned int line) {
    std::ostringstream msg;
    msg << std::endl << std::endl
        << "RUNTIME ERROR:"
        << std::endl
        << "hope " << expr << " disappointed" << std::endl
        << "in " << function
        << " file " << filename << " line " << line;
    if (errno) msg << ": " << strerror(errno);
    msg << std::endl << std::endl;
    stackTrace(msg, 1);
    msg << std::endl
        << "PLEASE CONSIDER ADDING PROPER ERROR HANDLING !!!" << std::endl
        << std::endl;
    throw std::runtime_error(msg.str());
}

class ErrorSignalHandler {
    static volatile sig_atomic_t isHandlerActive;
    static void handler(int);
public:
    ErrorSignalHandler();
};

volatile sig_atomic_t ErrorSignalHandler::isHandlerActive = 0;

#ifdef _MSC_VER
void ErrorSignalHandler::handler(int sig) {
    if (!isHandlerActive) {
        isHandlerActive = 1;
        std::cerr << std::endl << std::endl
            << "PROGRAM DEFECTIVE:"
            << std::endl
            << (sig) << " occurred" << std::endl
            << std::endl;
        stackTrace(std::cerr, 1);
        std::cerr << std::endl;
    }
    signal(sig, SIG_DFL);
    raise(sig);
}
#else
void ErrorSignalHandler::handler(int sig) {
    if (!isHandlerActive) {
        isHandlerActive = 1;
        std::cerr << std::endl << std::endl
                  << "PROGRAM DEFECTIVE:"
                  << std::endl
                  << strsignal(sig) << " occurred" << std::endl
                  << std::endl;
        stackTrace(std::cerr, 1);
        std::cerr << std::endl;
    }
    signal(sig, SIG_DFL);
    raise(sig);
}
#endif
#ifndef _MSCVER
ErrorSignalHandler::ErrorSignalHandler() {
    signal(SIGFPE,  handler);
    signal(SIGILL,  handler);
    signal(SIGSEGV, handler);
}
#else
ErrorSignalHandler::ErrorSignalHandler() {
    signal(SIGBUS, handler);
    signal(SIGFPE, handler);
    signal(SIGILL, handler);
    signal(SIGSEGV, handler);
    signal(SIGSYS, handler);
}
#endif

#if 0
static ErrorSignalHandler errorSignalHandler;
#endif

} // namespace AssertionsPrivate
