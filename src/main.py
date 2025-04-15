import tkinter as tk
import time
from threading import Thread
from queue import Queue

MAX_PACKETS = 12
PACKET_WIDTH = 40
PACKET_HEIGHT = 30
PACKET_SPACING = 30
DELAY = 0.5

SENDER_Y1, SENDER_Y2 = 100, 180
RECEIVER_Y1, RECEIVER_Y2 = 300, 380
SENDER_CENTER_Y = (SENDER_Y1 + SENDER_Y2 - PACKET_HEIGHT) // 2
RECEIVER_CENTER_Y = (RECEIVER_Y1 + RECEIVER_Y2 - PACKET_HEIGHT) // 2


class SelectiveRepeatSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Selective Repeat Protocol Simulation")

        top_sentence = tk.Label(root, text="Selective Repeat Protocol Simulation", font=("Arial", 16))
        top_sentence.pack(pady=2)

        self.canvas = tk.Canvas(root, width=1400, height=500, bg="white")
        self.canvas.pack()

        layout_frame = tk.Frame(root)
        layout_frame.pack(fill=tk.X, pady=10)

        # Controls on the left
        controls = tk.Frame(layout_frame)
        controls.pack(side=tk.LEFT, padx=10)

        button_frame = tk.Frame(controls)
        button_frame.pack(anchor="w", pady=2)

        self.send_button = tk.Button(button_frame, text="Start", command=self.start_simulation)
        self.send_button.pack(side=tk.LEFT, padx=2)

        self.pause_button = tk.Button(button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=2)

        self.reset_button = tk.Button(button_frame, text="Reset", command=self.reset_simulation)
        self.reset_button.pack(side=tk.LEFT, padx=2)

        tk.Label(controls, text="Number of packets (max 12):").pack(anchor="w")
        self.num_packets = tk.IntVar(value=12)
        tk.Spinbox(controls, from_=1, to=12, textvariable=self.num_packets).pack(anchor="w")

        tk.Label(controls, text="\nEnter packet numbers to drop (comma-separated):").pack(anchor="w")
        self.drop_entry = tk.Entry(controls)
        self.drop_entry.pack(anchor="w")

        tk.Label(controls, text="Window Size (max 5):").pack(anchor="w")
        self.window_size_var = tk.IntVar(value=5)
        tk.Spinbox(controls, from_=1, to=5, textvariable=self.window_size_var).pack(anchor="w")

        tk.Label(controls, text="Simulation Speed:").pack(anchor="w")
        self.speed_var = tk.StringVar(value="Normal")
        tk.OptionMenu(controls, self.speed_var, "Slowest", "Slower", "Normal", "Faster", "Fastest").pack(anchor="w")

        # Order tracking displays in the center
        order_frame = tk.Frame(layout_frame)
        order_frame.pack(side=tk.LEFT, padx=10, fill=tk.Y)

        # Received order display
        received_frame = tk.LabelFrame(order_frame, text="Order in which packets received", padx=5, pady=5)
        received_frame.pack(fill=tk.X, pady=2)
        self.received_order_text = tk.Text(received_frame, height=2, width=40, font=("Courier", 10))
        self.received_order_text.pack(fill=tk.X)

        # Upper layer order display
        upper_frame = tk.LabelFrame(order_frame, text="Order in which packets sent to upper layer", padx=5, pady=5)
        upper_frame.pack(fill=tk.X, pady=2)
        self.upper_layer_text = tk.Text(upper_frame, height=2, width=40, font=("Courier", 10))
        self.upper_layer_text.pack(fill=tk.X)

        # Log box on the right
        self.log_text = tk.Text(layout_frame, height=14, width=50, font=("Arial", 9))
        self.log_text.pack(side=tk.RIGHT, padx=10)

        self.packets_to_drop = []
        self.window_start_index = 0
        self.packet_rects = []
        self.sender_packet_objects = []
        self.running_thread = None
        self.paused = False
        self.pause_button.config(text="Pause", state=tk.DISABLED)
        self.window_rect = None
        self.receiver_window_rect = None
        self.timeout_dropped_packets = {}
        self.acked_packets = set()
        self.timeout_labels = {}
        self.pending_timeout_retransmit = set()
        self.packets_in_transit = set()        # Track packets currently in transit
        self.processed_packets = set()        # Track packets that have been processed
        self.received_out_of_order = set()        # Track out-of-order packets
        self.timeout_label_x = 1300        # X position for timeout labels
        self.timeout_label_y = 20        # Initial Y position
        self.timeout_label_spacing = 20        # Vertical spacing between timeout labels
        self.receiver_packet_objects = {}        # Track packets at receiver
        self.retransmission_queue = Queue()        # Queue for packets waiting to be retransmitted
        self.animation_in_progress = False        # Track if an animation is in progress
        self.nack_labels = {} # Keep track of NACK labels

        # Arrays to keep track of packet order
        self.received_order = []        # Order in which packets were received
        self.upper_layer_order = []        # Order in which packets were sent to upper layer

        # In the __init__ method, add a new queue for timeout retransmissions with priority
        self.retransmission_queue = Queue()        # Keep existing queue for NACK retransmissions
        self.timeout_retransmission_queue = Queue()

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def update_received_order_display(self):
        """Update the display showing the order in which packets were received"""
        self.received_order_text.delete(1.0, tk.END)
        if self.received_order:
            order_text = "P" + ", P".join(map(str, self.received_order))
            self.received_order_text.insert(tk.END, order_text)
        self.received_order_text.see(tk.END)

    def update_upper_layer_display(self):
        """Update the display showing the order in which packets were sent to upper layer"""
        self.upper_layer_text.delete(1.0, tk.END)
        if self.upper_layer_order:
            order_text = "P" + ", P".join(map(str, self.upper_layer_order))
            self.upper_layer_text.insert(tk.END, order_text)
        self.upper_layer_text.see(tk.END)

    def get_delay(self):
        speed_map = {
            "Slowest": 2.0,
            "Slower": 1.5,
            "Normal": 1.0,
            "Faster": 0.7,
            "Fastest": 0.4,
        }
        return speed_map.get(self.speed_var.get(), 1.0)

    def reset_simulation(self):
        if self.running_thread and self.running_thread.is_alive():
            self.running_thread = None
        self.canvas.delete("all")
        self.packet_rects.clear()
        self.sender_packet_objects.clear()
        self.running_thread = None
        self.paused = False
        self.pause_button.config(text="Pause", state=tk.DISABLED)
        self.send_button.config(text="Start", state=tk.NORMAL)
        self.window_start_index = 0
        self.window_rect = None
        self.receiver_window_rect = None
        self.timeout_dropped_packets.clear()
        self.acked_packets.clear()
        self.pending_timeout_retransmit.clear()
        self.received_out_of_order.clear()
        self.receiver_packet_objects.clear()
        self.packets_in_transit.clear()
        self.processed_packets.clear()        # Reset processed packets tracker
        self.animation_in_progress = False        # Reset animation tracker
        self.nack_labels.clear() # Clear NACK labels
        # Reset order tracking arrays
        self.received_order.clear()
        self.upper_layer_order.clear()
        self.update_received_order_display()
        self.update_upper_layer_display()
        # Clear the retransmission queue
        while not self.retransmission_queue.empty():
            try:
                self.retransmission_queue.get_nowait()
            except:
                pass
        for label in self.timeout_labels.values():
            self.canvas.delete(label)
        self.timeout_labels.clear()
        self.log_text.delete(1.0, tk.END)

        while not self.retransmission_queue.empty():
            try:
                self.retransmission_queue.get_nowait()
            except:
                pass

        # Clear the timeout priority queue too
        while not self.timeout_retransmission_queue.empty():
            try:
                self.timeout_retransmission_queue.get_nowait()
            except:
                pass

    def toggle_pause(self):
        if self.running_thread and self.running_thread.is_alive():
            self.paused = not self.paused
            self.pause_button.config(text="Resume" if self.paused else "Pause")

    def wait_if_paused(self):
        while self.paused:
            time.sleep(0.1)

    def draw_layout(self):
        self.canvas.create_rectangle(50, SENDER_Y1, 950, SENDER_Y2, outline="black")
        self.canvas.create_text(50, SENDER_Y2 + 15, text="Sender", font=("Arial", 12, "bold"), anchor="n")

        self.canvas.create_rectangle(50, RECEIVER_Y1, 950, RECEIVER_Y2, outline="black")
        self.canvas.create_text(50, RECEIVER_Y2 + 15, text="Receiver", font=("Arial", 12, "bold"), anchor="n")

        # Draw legend
        self.draw_legend()

    def draw_legend(self):
        # Legend box
        legend_x = 980
        legend_y = 100
        legend_width = 319
        legend_height = 300

        # Draw legend box
        self.canvas.create_rectangle(legend_x, legend_y,
                                     legend_x + legend_width,
                                     legend_y + legend_height,
                                     fill="#f5f5f5", outline="black")

        # Legend Title
        self.canvas.create_text(legend_x + legend_width / 2, legend_y + 20,
                                 text="PACKET TYPES",
                                 font=("Arial", 14, "bold"))

        # Sample packets
        sample_width = 30
        sample_height = 25
        text_offset = 110        # Text offset from left edge of legend

        # Blue packet - Sender packet
        y_pos = legend_y + 60
        self.canvas.create_rectangle(legend_x + 20, y_pos,
                                     legend_x + 20 + sample_width,
                                     y_pos + sample_height,
                                     fill="blue")
        self.canvas.create_text(legend_x + 35, y_pos + sample_height / 2,
                                 text="P0", fill="white",
                                 font=("Arial", 9, "bold"))
        self.canvas.create_text(legend_x + text_offset, y_pos + sample_height / 2,
                                 text="Sender packet",
                                 font=("Arial", 10),
                                 anchor="w")

        # Orange packet - Retransmitted packet
        y_pos += 40
        self.canvas.create_rectangle(legend_x + 20, y_pos,
                                     legend_x + 20 + sample_width,
                                     y_pos + sample_height,
                                     fill="orange")
        self.canvas.create_text(legend_x + 35, y_pos + sample_height / 2,
                                 text="P0", fill="white",
                                 font=("Arial", 9, "bold"))
        self.canvas.create_text(legend_x + text_offset, y_pos + sample_height / 2,
                                 text="Successfully retransmitted packet",
                                 font=("Arial", 10),
                                 anchor="w")

        # Green packet - Received in order
        y_pos += 40
        self.canvas.create_rectangle(legend_x + 20, y_pos,
                                     legend_x + 20 + sample_width,
                                     y_pos + sample_height,
                                     fill="green")
        self.canvas.create_text(legend_x + 35, y_pos + sample_height / 2,
                                 text="P0", fill="white",
                                 font=("Arial", 9, "bold"))
        self.canvas.create_text(legend_x + text_offset, y_pos + sample_height / 2,
                                 text="Received in order",
                                 font=("Arial", 10),
                                 anchor="w")

        # Yellow packet - Out of order
        y_pos += 40
        self.canvas.create_rectangle(legend_x + 20, y_pos,
                                     legend_x + 20 + sample_width,
                                     y_pos + sample_height,
                                     fill="#c9a200")        # Dark yellow
        self.canvas.create_text(legend_x + 35, y_pos + sample_height / 2,
                                 text="P2", fill="white",
                                 font=("Arial", 9, "bold"))
        self.canvas.create_text(legend_x + text_offset, y_pos + sample_height / 2,
                                 text="Received out of order",
                                 font=("Arial", 10),
                                 anchor="w")

        y_pos += 40        # Adjust position based on where your last legend item is
        self.canvas.create_rectangle(legend_x + 20, y_pos,
                                     legend_x + 20 + sample_width,
                                     y_pos + sample_height,
                                     fill="red")
        self.canvas.create_text(legend_x + 35, y_pos + sample_height / 2,
                                 text="P0", fill="white",
                                 font=("Arial", 9, "bold"))
        self.canvas.create_text(legend_x + text_offset, y_pos + sample_height / 2,
                                 text="Error packet (triggers NACK)",
                                 font=("Arial", 10),
                                 anchor="w")

        # Window indicator
        y_pos += 40
        self.canvas.create_rectangle(legend_x + 20, y_pos,
                                     legend_x + 50,
                                     y_pos + 30,
                                     outline="#c9a200",
                                     width=3)
        self.canvas.create_text(legend_x + text_offset, y_pos + 15,
                                 text="Sliding window",
                                 font=("Arial", 10),
                                 anchor="w")

    def draw_packet(self, x, y, text, color):
        rect = self.canvas.create_rectangle(x, y, x + PACKET_WIDTH, y + PACKET_HEIGHT, fill=color)
        label = self.canvas.create_text(x + 20, y + 15, text=text, fill="white", font=("Arial", 10, "bold"),
                                         justify=['center'])
        return rect, label

    def get_packet_x(self, index, total_packets):
        total_width = total_packets * PACKET_WIDTH + (total_packets - 1) * PACKET_SPACING
        start_x = (1000 - total_width) // 2
        return start_x + index * (PACKET_WIDTH + PACKET_SPACING)

    def update_window_rect(self, start, size):
        if self.window_rect:
            self.canvas.delete(self.window_rect)
        if self.receiver_window_rect:
            self.canvas.delete(self.receiver_window_rect)
        if start >= self.num_packets.get():
            return
        end = min(start + size, self.num_packets.get())
        x1 = self.get_packet_x(start, self.num_packets.get()) - 8
        x2 = self.get_packet_x(end - 1, self.num_packets.get()) + PACKET_WIDTH + 8
        self.window_rect = self.canvas.create_rectangle(x1, SENDER_Y1, x2, SENDER_Y2, outline="#c9a200", width=3)
        self.receiver_window_rect = self.canvas.create_rectangle(x1, RECEIVER_Y1, x2, RECEIVER_Y2, outline="#c9a200", width=3)

    def animate_packet(self, packet_id, is_dropped, is_retransmit=False):
        self.wait_if_paused()
        self.animation_in_progress = True
        # Mark packet as in transit
        self.packets_in_transit.add(packet_id)

        num_packets = self.num_packets.get()
        x_start = self.get_packet_x(packet_id, num_packets)
        y_start = SENDER_CENTER_Y
        y_end = RECEIVER_CENTER_Y

        packet_color = "blue" if not is_retransmit else "orange"
        rect, label = self.draw_packet(x_start, y_start, f"P{packet_id}", packet_color)
        self.canvas.update()

        total_distance = y_end - y_start
        animation_duration = 1.0 * self.get_delay()    # Increased duration for slower speed
        num_frames = 60    # More frames for smoother animation
        delay_per_frame = animation_duration / num_frames

        dy = total_distance / num_frames

        for _ in range(num_frames):
            self.wait_if_paused()
            self.canvas.move(rect, 0, dy)
            self.canvas.move(label, 0, dy)
            self.canvas.update()
            time.sleep(delay_per_frame)

        # Remove from transit since packet has completed its journey
        self.packets_in_transit.remove(packet_id)

        if is_dropped:
            # Show packet with error at receiver
            self.canvas.itemconfig(rect, fill="red")
            self.canvas.itemconfig(label, text=f"P{packet_id} ERR")
            self.log(f"Packet P{packet_id} received with errors (dropped)")

            # Show NACK going back to sender
            nack_line = self.canvas.create_line(x_start + 20, RECEIVER_Y1, x_start + 20, SENDER_Y2, arrow=tk.LAST, fill="red", width=2, dash=(4, 2))
            nack_text = self.canvas.create_text(x_start + 20, SENDER_Y1 + 10, text=f"NACK {packet_id}", fill="red", font=("Arial", 9, "bold"))
            self.nack_labels[packet_id] = (nack_line, nack_text)
            self.canvas.update()
            self.log(f"NACK sent for P{packet_id}")

            # Delete packet after short delay
            self.canvas.update()
            time.sleep(0.5 * self.get_delay()) # Increased delay
            self.canvas.delete(rect)
            self.canvas.delete(label)

            # Queue for immediate retransmission if not already queued
            if packet_id not in self.retransmission_queue.queue and packet_id not in [item for item in self.timeout_retransmission_queue.queue] and packet_id not in self.acked_packets:
                self.retransmission_queue.put(packet_id)
                self.log(f"NACK received for P{packet_id}, queued for retransmission")

            # Mark as pending retransmission to avoid timeout triggering immediately
            if packet_id not in self.pending_timeout_retransmit:
                self.pending_timeout_retransmit.add(packet_id)

        else:
            # Add this packet to the received order list and update display
            self.received_order.append(packet_id)
            self.update_received_order_display()

            in_order = packet_id == self.window_start_index

            # For out-of-order packet handling
            color = "green"
            if not in_order:
                color = "#c9a200" # Yellow for out-of-order packets
                if packet_id not in self.received_out_of_order:
                    self.received_out_of_order.add(packet_id)
                    self.log(f"Out-of-order packet P{packet_id} received and buffered")
            elif is_retransmit:
                color = "orange" # Orange for retransmitted packets

            self.canvas.itemconfig(rect, fill=color)
            self.canvas.itemconfig(label, text=f"P{packet_id} OK")

            # Place the packet at the receiver side
            rx, ry = x_start, RECEIVER_CENTER_Y
            receiver_rect, receiver_label = self.draw_packet(rx, ry, f"P{packet_id}", color)
            self.receiver_packet_objects[packet_id] = (receiver_rect, receiver_label)

            # If packet is in order, add it to upper layer order
            if in_order:
                self.upper_layer_order.append(packet_id)
                self.update_upper_layer_display()
                self.log(f"Packet P{packet_id} sent to upper layer")

            # Send ACK back to sender
            self.show_ack(packet_id, x_start + 20)
            self.canvas.update()
            time.sleep(0.5 * self.get_delay()) # Increased delay

            # Remove the packet in motion
            self.canvas.delete(rect)
            self.canvas.delete(label)

            if packet_id in self.sender_packet_objects and len(self.sender_packet_objects) > packet_id:
                sender_objects = self.sender_packet_objects[packet_id]
                if sender_objects and len(sender_objects) >= 2:
                    sender_rect, sender_label = sender_objects
                    if is_retransmit:
                        self.canvas.itemconfig(sender_rect, fill="#c9a200") # Change sender side color to yellow
                        self.canvas.itemconfig(sender_label, fill="black") # Ensure text is visible

            self.acked_packets.add(packet_id)

            # Clean up timeout label if exists
            if packet_id in self.timeout_labels:
                self.canvas.delete(self.timeout_labels[packet_id])
                del self.timeout_labels[packet_id]
            if packet_id in self.timeout_dropped_packets:
                del self.timeout_dropped_packets[packet_id]
            if packet_id in self.pending_timeout_retransmit:
                self.pending_timeout_retransmit.remove(packet_id)

            self.check_window_advancement()

        # Mark packet as processed
        self.processed_packets.add(packet_id)
        self.animation_in_progress = False

    def show_nack(self, packet_id, x):
        """Visualize a NACK being sent from receiver to sender"""
        nack_line = self.canvas.create_line(x, RECEIVER_Y1, x, SENDER_Y2, arrow=tk.LAST, fill="red", width=2, dash=(4, 2))
        nack_text = self.canvas.create_text(x, SENDER_Y1 + 10, text=f"NACK {packet_id}", fill="red", font=("Arial", 9, "bold"))
        self.nack_labels[packet_id] = (nack_line, nack_text)
        self.canvas.update()
        self.log(f"NACK sent for P{packet_id}")

    def check_window_advancement(self):
        """Check if window can be advanced based on received ACKs"""
        num_packets = self.num_packets.get()
        window_size = self.window_size_var.get()

        # Find consecutive packets that have been ACKed
        while self.window_start_index < num_packets and self.window_start_index in self.acked_packets:
            # Update receiver window visualization
            if self.window_start_index in self.received_out_of_order:
                self.received_out_of_order.remove(self.window_start_index)
                # Change color from yellow to green
                if self.window_start_index in self.receiver_packet_objects:
                    rect, label = self.receiver_packet_objects[self.window_start_index]
                    self.canvas.itemconfig(rect, fill="green")
                self.log(f"Packet P{self.window_start_index} now in order")

            # Add to upper layer order as it's now in order
            self.upper_layer_order.append(self.window_start_index)
            self.update_upper_layer_display()
            self.log(f"Packet P{self.window_start_index} sent to upper layer")

            self.window_start_index += 1
            self.update_window_rect(self.window_start_index, window_size)
            self.log(f"Window advanced to P{self.window_start_index}")
            # After advancing, remove any NACK visualization for the newly ACKed packet
            if self.window_start_index - 1 in self.nack_labels:
                nack_line, nack_text = self.nack_labels.pop(self.window_start_index - 1)
                self.canvas.delete(nack_line)
                self.canvas.delete(nack_text)

    def show_ack(self, packet_id, x):
        self.canvas.create_line(x, RECEIVER_Y1, x, SENDER_Y2, arrow=tk.LAST, fill="darkgreen", width=2)
        self.canvas.create_text(x, SENDER_Y1 + 10, text=f"ACK {packet_id}", fill="darkgreen", font=("Arial", 9, "bold"))
        self.canvas.update()
        self.log(f"ACK sent for P{packet_id}")

    def process_retransmission_queue(self):
        """Process any pending retransmissions, prioritizing timeout packets"""
        if not self.animation_in_progress and not self.packets_in_transit:
            # First check timeout queue (higher priority)
            if not self.timeout_retransmission_queue.empty():
                packet_id = self.timeout_retransmission_queue.get()
                if packet_id not in self.acked_packets:
                    self.log(f"Retransmitting P{packet_id} after Timeout (high priority)")
                    self.animate_packet(packet_id, False, True)
                    # Remove NACK visualization after retransmission starts
                    if packet_id in self.nack_labels:
                        nack_line, nack_text = self.nack_labels.pop(packet_id)
                        self.canvas.delete(nack_line)
                        self.canvas.delete(nack_text)
            # Then check NACK queue (lower priority)
            elif not self.retransmission_queue.empty():
                packet_id = self.retransmission_queue.get()
                if packet_id not in self.acked_packets:
                    self.log(f"Retransmitting P{packet_id} after NACK (lower priority)")
                    self.animate_packet(packet_id, False, True)
                    # Remove NACK visualization after retransmission starts
                    if packet_id in self.nack_labels:
                        nack_line, nack_text = self.nack_labels.pop(packet_id)
                        self.canvas.delete(nack_line)
                        self.canvas.delete(nack_text)
        self.root.after(200, self.process_retransmission_queue) # Increased delay for slower processing

    def start_timeout_watcher(self):
        def watcher():
            while self.running_thread is not None:
                now = time.time()
                # Make a copy of the dictionary items to avoid modification during iteration
                for idx, (packet_id, drop_time) in enumerate(list(self.timeout_dropped_packets.items())):
                    if packet_id in self.acked_packets:
                        # Clean up if packet was ACKed
                        if packet_id in self.timeout_labels:
                            self.canvas.delete(self.timeout_labels[packet_id])
                            del self.timeout_labels[packet_id]
                        if packet_id in self.pending_timeout_retransmit:
                            self.pending_timeout_retransmit.remove(packet_id)
                        del self.timeout_dropped_packets[packet_id]
                        # Also remove NACK visualization if it exists
                        if packet_id in self.nack_labels:
                            nack_line, nack_text = self.nack_labels.pop(packet_id)
                            self.canvas.delete(nack_line)
                            self.canvas.delete(nack_text)
                        continue

                    elapsed = now - drop_time
                    remaining = max(0, 5 - int(elapsed))

                    # Use the predefined position variables
                    y_pos = self.timeout_label_y + idx * self.timeout_label_spacing

                    if packet_id not in self.timeout_labels:
                        self.timeout_labels[packet_id] = self.canvas.create_text(
                            self.timeout_label_x, y_pos,
                            text=f"P{packet_id} timeout in: {remaining}s",
                            font=("Arial", 12, "bold"),
                            fill="red"
                        )
                    else:
                        self.canvas.itemconfig(self.timeout_labels[packet_id],
                                                text=f"P{packet_id} timeout in: {remaining}s")

                    if elapsed >= 5 and packet_id in self.pending_timeout_retransmit:
                        if packet_id not in self.acked_packets:
                            self.log(f"Timeout for P{packet_id}, queued for high-priority retransmission")

                            # Make sure to clean up the timeout label
                            if packet_id in self.timeout_labels:
                                self.canvas.delete(self.timeout_labels[packet_id])
                                del self.timeout_labels[packet_id]

                            # Queue the packet for high-priority retransmission only if not already in the other queue
                            if packet_id not in self.retransmission_queue.queue and packet_id not in [item for item in self.timeout_retransmission_queue.queue]:
                                self.timeout_retransmission_queue.put(packet_id)

                            # Remove from pending timeout list to prevent multiple retransmissions
                            if packet_id in self.pending_timeout_retransmit:
                                self.pending_timeout_retransmit.remove(packet_id)
                            # Remove from timeout_dropped_packets to prevent multiple timeouts
                            if packet_id in self.timeout_dropped_packets:
                                del self.timeout_dropped_packets[packet_id]
                            # Remove NACK visualization upon timeout retransmission
                            if packet_id in self.nack_labels:
                                nack_line, nack_text = self.nack_labels.pop(packet_id)
                                self.canvas.delete(nack_line)
                                self.canvas.delete(nack_text)

                            self.canvas.update()
                            time.sleep(1.0) # Reduced delay

                time.sleep(0.5) # Increased delay for checking timeouts
        Thread(target=watcher, daemon=True).start()
        
    def is_packet_in_current_window(self, packet_id):
        """Check if a packet is within the current sliding window"""
        window_end = min(self.window_start_index + self.window_size_var.get(), self.num_packets.get())
        return self.window_start_index <= packet_id < window_end

    def simulate_packets_sliding_window(self, num_packets):
        window_size = self.window_size_var.get()

        self.start_timeout_watcher()
        # Start processing retransmissions
        self.process_retransmission_queue()

        while self.window_start_index < num_packets:
            self.wait_if_paused()
            window_end = min(self.window_start_index + window_size, num_packets)
            current_window = list(range(self.window_start_index, window_end))

            self.update_window_rect(self.window_start_index, window_size)

            # Check if there's already an animation in progress
            while self.animation_in_progress or self.packets_in_transit:
                time.sleep(0.2) # Increased delay
                self.wait_if_paused()

            # Send packets only in the current window that haven't been processed or are in transit
            for packet_id in current_window:
                self.wait_if_paused()
                if self.running_thread is None:
                    return

                # Skip packets that are already acknowledged or in transit
                if packet_id in self.acked_packets or packet_id in self.pending_timeout_retransmit or packet_id in self.packets_in_transit:
                    continue

                # Skip packets that have already been processed (sent once) unless they need retransmission
                if packet_id in self.processed_packets and packet_id not in self.retransmission_queue.queue and packet_id not in [item for item in self.timeout_retransmission_queue.queue]:
                    continue

                # Process one packet at a time
                dropped = packet_id in self.packets_to_drop
                self.animate_packet(packet_id, dropped, is_retransmit=(packet_id in self.retransmission_queue.queue or packet_id in [item for item in self.timeout_retransmission_queue.queue]))

                # Wait for this animation to complete before sending the next packet
                while self.animation_in_progress or self.packets_in_transit:
                    time.sleep(0.2) # Increased delay
                    self.wait_if_paused()

            # Give time for any retransmissions to be processed
            time.sleep(0.6 * self.get_delay()) # Increased delay

            # If all packets in the current window have been processed and no retransmissions are pending,
            # but the window hasn't advanced, there might be an issue. Check if we should force window advancement.
            all_acked_in_window = True
            for packet_id in current_window:
                if packet_id not in self.acked_packets:
                    all_acked_in_window = False
                    break

            if all_acked_in_window and self.retransmission_queue.empty() and self.timeout_retransmission_queue.empty():
                # Double-check if window needs to advance
                self.check_window_advancement()

    def parse_drop_packets(self):
        """Parse and validate user input for packets to drop"""
        raw_input = self.drop_entry.get().strip()
        if not raw_input:
            return []

        try:
            packets = []
            for item in raw_input.split(','):
                item = item.strip()
                if item:
                    try:
                        packet_id = int(item)
                        if 0 <= packet_id < self.num_packets.get():
                            packets.append(packet_id)
                            self.log(f"Packet P{packet_id} will be dropped, triggering NACK.")
                        else:
                            self.log(
                                f"Warning: Invalid packet number '{item}'. Must be between 0 and {self.num_packets.get() - 1}."
                            )
                    except ValueError:
                        self.log(f"Warning: Invalid input '{item}'. Please use comma-separated integers.")
            return packets
        except Exception as e:
            self.log(f"Error parsing drop packets: {e}")
            return []

    def start_simulation(self):
        if self.running_thread is None or not self.running_thread.is_alive():
            self.reset_simulation()
            self.draw_layout()
            self.packets_to_drop = self.parse_drop_packets()
            num_packets = self.num_packets.get()
            # Initialize sender packets visually
            self.sender_packet_objects = []
            start_x = self.get_packet_x(0, num_packets)
            for i in range(num_packets):
                x = start_x + i * (PACKET_WIDTH + PACKET_SPACING)
                y = SENDER_CENTER_Y
                rect, label = self.draw_packet(x, y, f"P{i}", "blue")
                self.sender_packet_objects.append((rect, label))

            self.running_thread = Thread(target=self.simulate_packets_sliding_window, args=(num_packets,))
            self.running_thread.start()
            self.send_button.config(text="Restart", state=tk.NORMAL)
            self.pause_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
        else:
            self.log("Simulation is already running. Press 'Reset' to start a new one.")

    def on_closing(self):
        self.running_thread = None
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    simulator = SelectiveRepeatSimulator(root)
    root.protocol("WM_DELETE_WINDOW", simulator.on_closing)
    root.mainloop()