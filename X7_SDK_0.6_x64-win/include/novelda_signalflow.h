#ifndef NOVELDA_SIGNALFLOW_H
#define NOVELDA_SIGNALFLOW_H

#include <stddef.h>
#include <stdint.h>

#ifdef __EMSCRIPTEN__
    #include <emscripten.h>
#endif


#ifdef __cplusplus
extern "C"
{
#endif

///
/// @file novelda_signalflow.h
///
/// The SignalFlow C API allows to use SignalFlow from within a C/C++
/// application, even in bare metal context. SignalFlow is a dataflow
/// processing application featuring processing nodes that are connected to
/// each other. It provides the infrastructure to (de-)serialize and transport
/// data between nodes, but also to set parameters. The description of a node
/// structure and corresponding parameters is called a SignalFlow algorithm.
/// SignalFlow executes the nodes in correct order according to the algorithm
/// description.
///
/// The application life-cycle is as follows:
///
/// 1. Create a SignalFlow instance with signalflow_create(),
///
/// 2. Load an algorithm either from a .sfl file using signalflow_parse_flow_linear()
///    or in bare-metal context using signalflow_load_flow_ref(),
///
/// 3. Optionally set additional parameters using signalflow_set_parameters()
///    or signalflow_set_parameter_array(),
/// 
/// 4. At this point there are two options for executing the algorithm;
///     - Blocking mode which will run until cancelled.
///     - Single step mode which is driven by the application.
/// 
/// Blocking mode:
///     Execute the algorithm with signalflow_run().
/// 
/// Single step mode:
///     1. Initialize the algorithm with signalflow_initialize_flow()
///     2. Execute a single step/cycle of the algorithm with signalflow_run_flow_once()
///         - This step can be repeated until the application completes or an error occurs.
///     3. Cleanup the algorithm with signalflow_cleanup_flow()
/// 
///
/// Output data may be extracted by implementing the
/// signalflow_output_tap_fun_t function and installing it as a service using
/// signalflow_set_host_services().
///

///
/// \brief The context object of a SignalFlow instance that holds the execution state
///
typedef struct signalflow_context signalflow_context_t;

///
/// \brief The desired run state returned by the user-defined signalflow_cancel_fun_t
/// handler.
///
typedef enum signalflow_runstate
{
    SF_RUNSTATE_RUN, ///< Keep running for another round
    SF_RUNSTATE_CANCEL, ///< Abort signalflow_run()
} signalflow_runstate_t;

///
/// @brief Result values returned by SignalFlow nodes.
///
/// The value tells the scheduler what to do next.
///
typedef enum signalflow_processresult
{
    SF_PROCESS_CONTINUE,
    SF_PROCESS_BREAK,
    SF_PROCESS_ENDOFDATA,
} signalflow_processresult_t;

///
/// \brief Callback that allows the user to abort a running flow.
///
typedef signalflow_runstate_t (*signalflow_cancel_fun_t)( void *cancel_context );

///
/// \brief Error codes used in the SignalFlow API
///
typedef int32_t signalflow_error_t;

///
/// \brief A flow identifier used in bundle packages
///
typedef uint32_t signalflow_ref_t;


#define SFERR_SUCCESS 0
#define SFERR_FAILURE -1
#define SFERR_NOT_IMPLEMENTED -2
#define SFERR_NULLPTR -3
#define SFERR_INVALID_ARGUMENT -4
#define SFERR_FLOW_CONFIGURATION -5
#define SFERR_FLOW_LOAD -6
#define SFERR_FILE_ERROR -7
#define SFERR_ARRAY_NOT_FOUND -8
#define SFERR_INVALID_FLOW_REF -9

///
/// \brief Possible data types in SignalFlow parameters and values
///
/// \sa signalflow_set_parameter_array(), signalflow_output_tap_fun_t
///
typedef uint16_t signalflow_datatype_t;

#define SF_DATATYPE_BOOL 0
#define SF_DATATYPE_UINT32 1
#define SF_DATATYPE_INT32 2
#define SF_DATATYPE_FLOAT 3
#define SF_DATATYPE_DOUBLE 4
#define SF_DATATYPE_UINT8 6
#define SF_DATATYPE_STRING 7
#define SF_DATATYPE_UINT16 8
#define SF_DATATYPE_INT16 9


#ifdef BUILDING_NOVELDA_SIGNALFLOW
    // When building a dynamic library
    #ifdef _MSC_VER 
        #define SF_SYMBOL_EXPORT __declspec(dllexport)
    #else // _MSC_VER
        #define SF_SYMBOL_EXPORT __attribute__ ((visibility ("default")))
    #endif // _MSC_VER
#elif defined(USING_NOVELDA_SIGNALFLOW)
    // When using a dynamic library
    #ifdef _MSC_VER
        #define SF_SYMBOL_EXPORT __declspec(dllimport)
    #else // _MSC_VER
        #define SF_SYMBOL_EXPORT
    #endif // _MSC_VER
#else
    // When building/using a static library
    #ifdef __EMSCRIPTEN__
        #define SF_SYMBOL_EXPORT EMSCRIPTEN_KEEPALIVE
    #else
        #define SF_SYMBOL_EXPORT
    #endif
#endif // BUILDING_NOVELDA_SIGNALFLOW


/// @brief Creates a signalflow context object
///
/// This function allocates memory for a SignalFlow and initializes all needed
/// resources.
///
/// @param argv reserved for future use, set it to NULL
/// @param argc reserved for future use, set it to 0
/// @return A SignalFlow context object on success, NULL otherwise
///
SF_SYMBOL_EXPORT signalflow_context_t* signalflow_create( const char* argv[], size_t argc );

/// @brief Loads an .sfl file containing a binary flow description
///
/// This function is not available in bare metal environments.
///
/// @param ctx 
/// @param flow_buffer the file content
/// @param flow_buffer_size the file length in bytes
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_parse_flow_linear( signalflow_context_t *ctx, const uint8_t* flow_buffer, size_t flow_buffer_size );

/// @brief Load an algorithm by reference id from a pre-built bundle
///
/// SignalFlow can run different algorithms. The prebuilt bundle comes with one
/// or more embedded algorithms which are identified by an id. This function
/// loads an algorithm by its \a flow_ref id and prepares SignalFlow for
/// execution with signalflow_run(). Additional parameters may be set before
/// execution.
///
/// @param ctx 
/// @param flow_ref the flow reference id, a 32 bit hash
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_load_flow_ref( signalflow_context_t *ctx, signalflow_ref_t flow_ref );

/// @brief Load linear flow from .sfl file.
///
/// @param ctx 
/// @param flow_linear_file path to .sfl file
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_load_flow_linear(signalflow_context_t* ctx, const char* flow_linear_file );

/// @brief Load flow from .sfw file.
///
/// @param ctx 
/// @param flow_file path to .sfw file
/// @param variables optional list of variables
/// @param variable_count number of variables in list
/// @param augment_flow_file optional path to augment flow file
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_load_flow(signalflow_context_t* ctx, const char* flow_file, const char* variables[], size_t variable_count, const char* augment_flow_file );

///
/// @brief Sets binary parameter blobs on loaded flow
///
/// Although a flow comes with default parameters, it might be desired to
/// change some algorithm properties at run-time. This function accepts binary
/// parameter blobs as input and updates the SignalFlow nodes. A parameter blob
/// may consist of various parameters.
///
/// @param ctx 
/// @param param_buffer the binary parameter blob
/// @param param_buffer_size size of \a param_buffer in bytes
/// @return SFERR_SUCCESS on success, otherwise an error code
/// @sa signalflow_set_parameter_array()
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_set_parameters( signalflow_context_t *ctx, const uint8_t* param_buffer, size_t param_buffer_size );

/// @brief Set parameter on loaded flow using parameter set/array semantics and
/// section/parameter id (fnv1a hash)
///
/// SignalFlow algorithm parameters can be used to customize an algorithm. Each
/// parameter has a certain \a parameter_id and is located under a certain
/// section. In addition, it may have a semantic (\a semantic_id) assigned.
/// The correct ids and values have to be provided by Novelda.
///
/// Parameter values are always represented by arrays which may have a shape.
/// Scalar values can be thought of as 1-dimensional arrays of a single value.
///
/// This function may be called before signalflow_run() or at run-time during
/// one of the numerous callbacks. It is neither thread-safe nor reentrant.
///
/// @param ctx 
/// @param parameterset_semantic 
/// @param section_id 
/// @param parameter_id 
/// @param datatype 
/// @param shape 
/// @param shape_size 
/// @param array_buffer 
/// @param array_element_count number of elements of type \a datatype in \a array_buffer
/// @return SFERR_SUCCESS on success, otherwise an error code
/// @sa signalflow_set_parameters()
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_set_parameter_array(
    signalflow_context_t* ctx,
    uint32_t parameterset_semantic,
    uint32_t section_id,
    uint32_t parameter_id,
    signalflow_datatype_t datatype,
    const uint16_t* shape, size_t shape_size,
    const uint8_t* array_buffer, size_t array_element_count );

/// @brief Get parameter on loaded flow using parameter set/array semantics and
/// section/parameter id (fnv1a hash)
///
/// SignalFlow algorithm parameters can be used to customize an algorithm. Each
/// parameter has a certain \a parameter_id and is located under a certain
/// section. In addition, it may have a semantic (\a semantic_id) assigned.
/// The correct ids and values have to be provided by Novelda.
///
/// Parameter values are always represented by arrays which may have a shape.
/// Scalar values can be thought of as 1-dimensional arrays of a single value.
///
/// Nodes in the flow are queried in flow order, the function will return
/// when a node successfully returns the parameter value.
/// 
/// This function may be called before signalflow_run() or at run-time during
/// one of the numerous callbacks. It is not thread-safe
///
/// @param ctx 
/// @param parameterset_semantic fnv1a hash of parameter set name
/// @param section_id fnv1a hash of section name
/// @param parameter_id fnv1a hash of parameter name
/// @param datatype pointer to where the extracted datatype shall be written
/// @param shape pointer to where the extracted shape shall be written (optional)
/// @param shape_size pointer to where the extracted shape size shall be written (optional)
/// @param array_buffer pointer to where the extracted array shall be written
/// @param array_element_count pointer to where the extracted array element count shall be written
/// @return SFERR_SUCCESS on success, SFERR_ARRAY_NOT_FOUND when parameter
/// is not found, otherwise an error code

SF_SYMBOL_EXPORT signalflow_error_t signalflow_get_parameter_array(
    signalflow_context_t* ctx,
    uint32_t parameterset_semantic,
    uint32_t section_id,
    uint32_t parameter_id,
    signalflow_datatype_t *datatype,
    const uint16_t** shape, size_t *shape_size,
    const uint8_t** array_buffer, size_t *array_element_count );

///
/// @brief Executes an algorithm
///
/// This function executes an algorithm loaded by signalflow_load_flow_ref() or
/// signalflow_parse_flow_linear(). After a setup phase. the algorithm runs in
/// cycles and after each cycle, SignalFlow executes the \a cancel_func
/// handler.
///
/// This function blocks until SignalFlow observes an error or until the \a
/// cancel_func handler returns SF_RUNSTATE_CANCEL. When a flow ends due to
/// empty input data or cancellation, all resources are cleaned up.
/// 
/// This function is equivalent to calling signalflow_initialize_flow(), a loop
/// of signalflow_run_flow_once(), followed by signalflow_deinitialize_flow().
///
/// @param ctx
/// @param cancel_func an optional callback handler that allows to abort the
///        current operation
/// @param cancel_context an optional parameter for signalflow_cancel_fun_t
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_run( signalflow_context_t *ctx, signalflow_cancel_fun_t cancel_func, void *cancel_context );

///
/// @brief Uninitializes and releases the context created by signalflow_create().
/// @param ctx
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_delete( signalflow_context_t *ctx );

///
/// @brief Inspects data produced by a SignalFlow node
///
/// SignalFlow nodes ususally produce output data which is forwarded to the
/// next node in the flow. This function hooks into the SignalFlow scheduler
/// and is called each time a node has produced some data. A data entity is
/// called signal frame. The node can be identified by \a node_name which is 32
/// bit id. The used data format is internal. Data may be extracted using the
/// signalflow_get_frame_array() function. This function is called from the
/// scheduler for each signal frame and is time critical i.e. no time-consuming
/// operations can be done here, instead, use a separate thread or similar.
/// Also note that the data pointers are only valid for the duration of the call,
/// so any data that is needed for later processing must be copied and stored in
/// a separate buffer.
///
typedef signalflow_error_t( *signalflow_output_tap_fun_t )(void *host_context, uint32_t node_name, const uint8_t* data_buffer, size_t data_buffer_size);

///
/// @brief Feeds data into a SignalFlow algorithm
///
/// SignalFlow consists of dataflow nodes that produce and consume data. A flow
/// usually consists of at least one source node. This function can be used as
/// an alternative interface. The used data format is internal.
///
typedef uint32_t (*signalflow_read_frame_fun_t)(void *host_context, uint32_t node_name, const uint8_t **frame_buffer, size_t *frame_buffer_size);

///
/// @brief Optional callback functions to interact with SignalFlow
///
/// Host services are callbacks provided by host application that may interact
/// with a currently running algorithm.
///
typedef struct signalflow_host_services
{
    signalflow_output_tap_fun_t output_tap; ///< Taps a SignalFlow node to inspect its output data
    signalflow_read_frame_fun_t read_frame; ///< Reads data in and forwards it to the first node in the cycle
} signalflow_host_services_t;


/// @brief Set services provided by host application
///
/// The \a host_services structure must live for the duration of the flow.
///
/// @param host_services Represents a list of services provided by the host
/// @param host_context 
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_set_host_services( signalflow_context_t* ctx, signalflow_host_services_t *host_services, void *host_context );


/// @brief Extracts data from a signal frame
///
/// SignalFlow consists of data flow nodes that consume and produce data. Each
/// data entity, also known as a signal frame, has a specific structure and
/// allows random access to individual values. Values are organized in
/// (multi-dimensional) arrays with a certain shape and a \a array_semantic id
/// and a \a data_type. Multiple arrays are combined in one signal frame,
/// identified by \a signal_semantic. Scalar values are stored as 1-dimensional
/// arrays of size 1. The shape is provided as a C array of uint16_t values,
/// each one measuring one dimension.
///
/// @param frame_buffer the signal frame as raw data
/// @param frame_buffer_size size of the signal frame in bytes
/// @param signal_semantic identifies a certain signal in the frame
/// @param array_semantic identifies a certain array in a signal
/// @param data_type specifies the data type in \a array_buffer
/// @param shape describes the n-dimensional shape of an array (optional)
/// @param shape_size specifies the length of \a shape and is equal to the number of dimensions (optional)
/// @param array_buffer pointer to where the extracted array shall be written
/// @param array_element_count number of elements reserved in \a array_buffer
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_get_frame_array(
    const uint8_t* frame_buffer, size_t frame_buffer_size,
    uint32_t signal_semantic, uint32_t array_semantic,
    signalflow_datatype_t* datatype,
    const uint16_t** shape, size_t *shape_size,
    const uint8_t** array_buffer, size_t* array_element_count );


/// @brief Extracts data from a signal frame's state change if present
///
/// A signal frame can contain state changes from the flow. State changes are used
/// to provide data about important changes in the internal state of the flow when
/// as they occur. State change parameter sets are organized in a hierarchy of sections
/// \a section_id with parameters. Parameter values are (multi-dimensional) arrays with
/// a certain shape and a \a parameter_id id and a \a datatype. Scalar values are stored
/// as 1-dimensional arrays of size 1. The shape is provided as a C array of uint16_t
/// values, each one measuring one dimension.
///
/// @param frame_buffer 
/// @param frame_buffer_size 
/// @param parameterset_semantic 
/// @param section_id 
/// @param parameter_id 
/// @param datatype 
/// @param shape 
/// @param shape_size 
/// @param array_buffer 
/// @param array_element_count 
/// @return SFERR_SUCCESS on success, otherwise an error code
/// 
SF_SYMBOL_EXPORT signalflow_error_t signalflow_get_frame_statechange_parameter_array(
    const uint8_t* frame_buffer, size_t frame_buffer_size,
    uint32_t parameterset_semantic,
    uint32_t section_id,
    uint32_t parameter_id,
    signalflow_datatype_t* datatype,
    const uint16_t** shape, size_t* shape_size,
    const uint8_t** array_buffer, size_t* array_element_count );


typedef struct {
    /// @brief Signal frame timestamp
    ///
    /// A signal frame can contain a timestamp. The timestamp is a 64 bit unsigned
    /// integer value that represents the time in milliseconds since the Unix epoch.
    ///
    uint64_t timestamp;

    /// @brief Signal frame sequence number
    ///
    /// A signal frame can contain a sequence number. The sequence number is a 32
    /// bit unsigned integer value where each 16 bit half is the sequence number of
    /// the corresponding channel.
    ///
    uint32_t sequence_number;
} signalflow_frame_info_t;

/// @brief Extracts frame info from a signal frame
///
/// Retrieves additional info from the signal frame.
/// See \ref signalflow_frame_info_t for more details.
///
/// @param frame_buffer the signal frame as raw data
/// @param frame_buffer_size size of the signal frame in bytes
/// @param frame_info pointer to where the extracted frame info shall be written
/// @return SFERR_SUCCESS on success, otherwise an error code
SF_SYMBOL_EXPORT signalflow_error_t signalflow_get_frame_info(
    const uint8_t* frame_buffer, size_t frame_buffer_size, signalflow_frame_info_t* frame_info );

///
/// @brief Callback function to output logging messages
///
/// When SignalFlow is built with logging support, this callback function can
/// be used to print them. Each logging messages has a \a level and a \a
/// message cstring.
///
/// A \a host_context argument can be set in signalflow_set_logger() containing
/// a user-defined value. That makes it easier to use SignalFlow in a thread or
/// task environment without global variables.
///
/// Note that the bare-metal build of SignalFlow has logging messages disabled.
/// When using this callback, logging events are observed with a certain level,
/// but the messages string is empty.
///
typedef void (*signalflow_log_output_fun_t)(void* host_context, uint32_t level, const char* message);

///
/// \brief Installs a logging handler function
///
/// \param log_handler the callback function to be used param host_context an
///        optional context argument that will be passed to the \a log_handler
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_set_logger( signalflow_log_output_fun_t log_handler, void* host_context );

typedef enum
{
    LOG_LEVEL_ERROR = 0,
    LOG_LEVEL_WARNING,
    LOG_LEVEL_INFO,
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_DEBUG1,
    LOG_LEVEL_DEBUG2,
    LOG_LEVEL_DEBUG3,
    LOG_LEVEL_DEBUG4
} signalflow_log_level_t;

///
/// \brief Sets the log level (defaults to LogLevel_Warning)
/// \param level the log level to be used
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_set_log_level( signalflow_log_level_t level );

///
/// \brief Writes the SignalFlow version to an array
///
/// The SignalFlow version array consists of 3 entries:
///
/// - [0]: major version
/// - [1]: minor version
/// - [2]: build counter
///
/// \param version the array to write the version digits to
/// @return SFERR_SUCCESS on success, otherwise an error code
///
SF_SYMBOL_EXPORT signalflow_error_t signalflow_get_version( uint32_t version[3] );

#ifdef __cplusplus
}
#endif

#endif // NOVELDA_SIGNALFLOW_H
