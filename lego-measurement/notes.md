# Gabriel Scalability Measurement Notes

## Gabriel Flow Mechanism

Existing gabriel flow mechanism is implemented as two major component. First is the flow control between client and server, managed by TokenController in the client and MAX_TOKEN_SIZE in the server config. Second is the flow control between the user control VM and the cognitive engine VM, which is controlled by APP_LEVEL_TOKEN_SIZE in the server config.

I encountered problems of some frame sent do not contain response back in 11/01. It turns out to be because of APP_LEVEL_TOKEN_SIZE is set to be 1 by default.

## Lego measurement

It seems that the backend bottleneck is less than 1 core. tried running 0.5 or 0.75 core, but they stuck at frame 835 or 850.
