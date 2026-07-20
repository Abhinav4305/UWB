#pragma once

#include "novelda_signalflow.h"
#include "novelda_signalflow_private.h"

#include <functional>
//
// C++ SignalFlow hosting helper class
//
namespace Novelda::SignalFlow
{

    class SignalFlowHost
    {
    public:
        using CancelFun = std::function<bool()>;
        using LoggerFun = std::function<void( uint32_t, const char* )>;

    private:
        signalflow_context_t *signalFlow_ = nullptr;

        bool explicitCancel_ = false;

        CancelFun cancelFun_;

        signalflow_runstate GetRunState()
        {
            if( explicitCancel_ )
                return SF_RUNSTATE_CANCEL;

            if( !cancelFun_ )
                return SF_RUNSTATE_RUN;

            return cancelFun_() ? SF_RUNSTATE_CANCEL : SF_RUNSTATE_RUN;
        }

    public:

        static bool SetLogger( LoggerFun loggerFun )
        {
            static LoggerFun loggerFun_;

            loggerFun_ = loggerFun;
            return signalflow_set_logger(
                []( void* ctx, uint32_t level, const char* message )
                {
                    LoggerFun& lf = *reinterpret_cast<LoggerFun*>(ctx);
                    lf( level, message );
                },
                &loggerFun_ );
        }

        SignalFlowHost()
        {
            Reset();
        }

        bool Reset()
        {
            Clear();
            signalFlow_ = signalflow_create( nullptr, 0 );
            return signalFlow_ != nullptr;
        }

        void Clear() noexcept
        {
            if( signalFlow_ != nullptr )
            {
                signalflow_delete( signalFlow_ );
                signalFlow_ = nullptr;
            }
        }

        signalflow_error_t LoadLinear( const uint8_t* linearFlowBuffer, size_t linearFlowBufferSize ) noexcept
        {
            if( signalFlow_ == nullptr )
                return 0;

            return signalflow_parse_flow_linear( signalFlow_, linearFlowBuffer, linearFlowBufferSize );
        }

        signalflow_error_t LoadLinear( const std::string &flowFilePath ) noexcept
        {
            return LoadLinear( flowFilePath.c_str() );
        }

        signalflow_error_t LoadLinear( const char *flowFilePath  ) noexcept
        {
            if( signalFlow_ == nullptr )
                return 0;

            return signalflow_load_flow_linear( signalFlow_, flowFilePath );
        }

        signalflow_error_t SetParameters( const uint8_t* parameterSet, size_t size ) noexcept
        {
            if( signalFlow_ == nullptr )
                return 0;
            
            return signalflow_set_parameters( signalFlow_, parameterSet, size );
        }

        signalflow_error_t SetParameters( const std::string& parameterSetFile ) noexcept
        {
            return SetParameters( parameterSetFile.c_str() );
        }

        signalflow_error_t SetParameters( const char* parameterSetFile ) noexcept
        {
            if( signalFlow_ == nullptr )
                return 0;

            return signalflow_set_parameters_from_file( signalFlow_, parameterSetFile );
        }

        signalflow_error_t Run( std::function<bool()> cancelFun ) noexcept
        {
            explicitCancel_ = false;
            cancelFun_ = cancelFun;
            return signalflow_run( signalFlow_,
                []( void* ctx ) -> signalflow_runstate
                {
                    return reinterpret_cast<SignalFlowHost*>(ctx)->GetRunState();
                },
                this );
        }

        void Cancel()
        {
            explicitCancel_ = true;
        }

        ~SignalFlowHost()
        {
            Clear();
        }
    };
}
