<?php
include('/etc/flag3');

// Method 1: Using exec() - Returns output as array
echo "=== Method 1: Using exec() ===\n";
exec('hostname', $output, $return_code);
echo "Hostname: " . $output[0] . "\n";
echo "Return code: " . $return_code . "\n\n";

// Method 2: Using shell_exec() - Returns output as string
echo "=== Method 2: Using shell_exec() ===\n";
$hostname = shell_exec('hostname');
echo "Hostname: " . trim($hostname) . "\n\n";

// Method 3: Using system() - Outputs directly and returns last line
echo "=== Method 3: Using system() ===\n";
echo "Hostname: ";
$last_line = system('hostname');
echo "\nLast line returned: " . $last_line . "\n\n";

// Method 4: Using passthru() - Outputs directly (no return value)
echo "=== Method 4: Using passthru() ===\n";
echo "Hostname: ";
passthru('hostname');
echo "\n\n";

// Method 5: Using backticks (`) - Similar to shell_exec()
echo "=== Method 5: Using backticks ===\n";
$hostname = `hostname`;
echo "Hostname: " . trim($hostname) . "\n\n";

// Method 6: Using proc_open() - Advanced method with more control
echo "=== Method 6: Using proc_open() ===\n";
$descriptors = array(
    0 => array("pipe", "r"),  // stdin
    1 => array("pipe", "w"),  // stdout
    2 => array("pipe", "w")   // stderr
);

$process = proc_open('hostname', $descriptors, $pipes);
if (is_resource($process)) {
    $hostname = stream_get_contents($pipes[1]);
    fclose($pipes[1]);
    proc_close($process);
    echo "Hostname: " . trim($hostname) . "\n\n";
}

// Simple one-liner examples
echo "=== Simple Examples ===\n";
echo "Quick hostname: " . trim(shell_exec('hostname')) . "\n";
echo "Quick hostname with backticks: " . trim(`hostname`) . "\n";
?>

