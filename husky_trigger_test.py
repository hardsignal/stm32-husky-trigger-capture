import chipwhisperer as cw

scope = cw.scope()

scope.clock.clkgen_src = "system"
scope.clock.clkgen_freq = 10e6
scope.clock.adc_mul = 4
scope.trigger.triggers = "tio4"
scope.adc.samples = 1000

success = 0

for i in range(10):
    scope.arm()
    timed_out = scope.capture()

    if not timed_out:
        success += 1
        print(f"Capture {i+1}: OK")
    else:
        print(f"Capture {i+1}: TIMEOUT")

print(f"\nResult: {success}/10 successful")

scope.dis()
